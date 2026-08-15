// TodoScope desktop shell. Thin by charter: spawn the Python sidecar, wait for
// /health, open a window on it, kill the sidecar on quit. Beyond lifecycle it
// carries only chrome: menu-driven zoom and the network-share toggle.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream, UdpSocket};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};

use tauri::menu::{CheckMenuItem, CheckMenuItemBuilder, MenuBuilder, MenuItemBuilder, SubmenuBuilder};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder, Wry};
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

/// true => ActivationPolicy::Accessory (no Dock icon) and closing the last
/// window keeps the app alive in the menu bar.
const MENU_BAR_ONLY: bool = false;

const READY_TIMEOUT: Duration = Duration::from_secs(15);
const ZOOM_STEP: f64 = 1.1;

struct ServerState {
    child: Mutex<Option<Child>>,
    port: u16,
    spawn_failed: bool,
    shared: Mutex<bool>,
    zoom: Mutex<f64>,
}

/// Tray checkbox for "Share on Network" — kept global so handlers can revert
/// its checked state when a toggle is refused.
static SHARE_ITEM: OnceLock<CheckMenuItem<Wry>> = OnceLock::new();

fn home_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/tmp".into()))
}

fn data_dir() -> PathBuf {
    home_dir().join(".todoscope")
}

fn port_file() -> PathBuf {
    data_dir().join("desktop-port")
}

fn share_file() -> PathBuf {
    data_dir().join("desktop-share")
}

fn zoom_file() -> PathBuf {
    data_dir().join("desktop-zoom")
}

/// OS-assigned port, remembered across launches: the WKWebView origin (and its
/// localStorage) is port-scoped, so reuse the last port while it stays free.
fn pick_port() -> u16 {
    if let Ok(saved) = std::fs::read_to_string(port_file()) {
        if let Ok(port) = saved.trim().parse::<u16>() {
            if port > 0 && TcpListener::bind(("127.0.0.1", port)).is_ok() {
                return port;
            }
        }
    }
    let port = TcpListener::bind(("127.0.0.1", 0))
        .expect("bind 127.0.0.1:0")
        .local_addr()
        .expect("local_addr")
        .port();
    let _ = std::fs::create_dir_all(data_dir());
    let _ = std::fs::write(port_file(), port.to_string());
    port
}

fn saved_share() -> bool {
    std::fs::read_to_string(share_file()).map(|s| s.trim() == "1").unwrap_or(false)
}

fn saved_zoom() -> f64 {
    std::fs::read_to_string(zoom_file())
        .ok()
        .and_then(|s| s.trim().parse::<f64>().ok())
        .filter(|z| (0.25..=4.0).contains(z))
        .unwrap_or(1.0)
}

/// The address teammates use: route-discovery trick, no packet is sent.
fn lan_ip() -> Option<String> {
    let socket = UdpSocket::bind("0.0.0.0:0").ok()?;
    socket.connect("8.8.8.8:80").ok()?;
    Some(socket.local_addr().ok()?.ip().to_string())
}

fn sidecar_exe() -> PathBuf {
    #[cfg(debug_assertions)]
    {
        // Dev without TODOSCOPE_DEV_PORT: repo-relative onedir build (make sidecar_dir).
        let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../dist/todoscope/todoscope");
        if dev.exists() {
            return dev;
        }
    }
    // Bundled: Contents/MacOS/TodoScope -> Contents/MacOS/todoscope-server/todoscope
    std::env::current_exe()
        .expect("current_exe")
        .parent()
        .expect("exe parent")
        .join("todoscope-server/todoscope")
}

fn spawn_sidecar(port: u16, shared: bool) -> std::io::Result<Child> {
    let exe = sidecar_exe();
    // Bundler copies have been known to drop the exec bit; harmless when already set.
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&exe, std::fs::Permissions::from_mode(0o755));
    }
    std::fs::create_dir_all(data_dir())?;
    let log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(data_dir().join("desktop-sidecar.log"))?;
    let host = if shared { "0.0.0.0" } else { "127.0.0.1" };
    // Args matter: zero args + no tty would send cli.py into pystray tray mode.
    // --exact-port keeps cli.py from silently hunting to a different port.
    Command::new(&exe)
        .args([
            "--port",
            &port.to_string(),
            "--host",
            host,
            "--no-browser",
            "--exact-port",
        ])
        .stdout(Stdio::from(log.try_clone()?))
        .stderr(Stdio::from(log))
        .spawn()
}

/// Raw HTTP/1.0 GET /health over loopback; returns the full response text.
fn health_body(port: u16) -> Option<String> {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).ok()?;
    stream.set_read_timeout(Some(Duration::from_millis(500))).ok()?;
    stream.set_write_timeout(Some(Duration::from_millis(500))).ok()?;
    write!(
        stream,
        "GET /health HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    )
    .ok()?;
    let mut buf = String::new();
    let _ = stream.read_to_string(&mut buf);
    Some(buf)
}

fn health_ok(port: u16) -> bool {
    health_body(port).is_some_and(|buf| {
        (buf.starts_with("HTTP/1.0 200") || buf.starts_with("HTTP/1.1 200"))
            && buf.contains("todoscope")
    })
}

/// Our own /health payload — a string probe beats a JSON dependency.
fn auth_enabled(port: u16) -> bool {
    health_body(port).is_some_and(|buf| buf.contains("\"auth\":true") || buf.contains("\"auth\": true"))
}

fn stop_sidecar(state: &ServerState) {
    let Some(mut child) = state.child.lock().unwrap().take() else {
        return;
    };
    // Onedir build: this is the real Python pid and cli.py handles SIGTERM cleanly.
    unsafe {
        libc::kill(child.id() as libc::pid_t, libc::SIGTERM);
    }
    let deadline = Instant::now() + Duration::from_secs(2);
    while Instant::now() < deadline {
        if matches!(child.try_wait(), Ok(Some(_))) {
            return;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    let _ = child.kill();
    let _ = child.wait();
}

fn apply_zoom(handle: &AppHandle, factor: f64) {
    if let Some(window) = handle.get_webview_window("main") {
        let _ = window.set_zoom(factor);
    }
    let _ = std::fs::write(zoom_file(), format!("{factor:.3}"));
}

fn zoom_by(handle: &AppHandle, op: impl Fn(f64) -> f64) {
    let state = handle.state::<ServerState>();
    let mut zoom = state.zoom.lock().unwrap();
    *zoom = op(*zoom).clamp(0.25, 4.0);
    apply_zoom(handle, *zoom);
}

fn open_main_window(handle: &AppHandle, port: u16) {
    let url: tauri::Url = format!("http://127.0.0.1:{port}/")
        .parse()
        .expect("localhost url");
    match WebviewWindowBuilder::new(handle, "main", WebviewUrl::External(url))
        .title("TodoScope")
        .inner_size(1200.0, 800.0)
        .zoom_hotkeys_enabled(true) // pinch-zoom gestures; Cmd keys ride the View menu
        .build()
    {
        Ok(window) => {
            let zoom = *handle.state::<ServerState>().zoom.lock().unwrap();
            if (zoom - 1.0).abs() > f64::EPSILON {
                let _ = window.set_zoom(zoom);
            }
        }
        Err(e) => eprintln!("window build failed: {e}"),
    }
}

fn sidecar_died(handle: &AppHandle) -> bool {
    let state = handle.state::<ServerState>();
    let mut guard = state.child.lock().unwrap();
    match guard.as_mut() {
        Some(child) => matches!(child.try_wait(), Ok(Some(_))),
        None => false, // TODOSCOPE_DEV_PORT mode: external server, nothing to watch
    }
}

fn fail_and_exit(handle: &AppHandle) {
    handle
        .dialog()
        .message(
            "TodoScope's server failed to start.\n\nSee ~/.todoscope/desktop-sidecar.log for details.",
        )
        .kind(MessageDialogKind::Error)
        .title("TodoScope")
        .blocking_show();
    handle.exit(1);
}

fn info_dialog(handle: &AppHandle, message: &str) {
    handle
        .dialog()
        .message(message)
        .kind(MessageDialogKind::Info)
        .title("TodoScope")
        .blocking_show();
}

fn set_share_checked(checked: bool) {
    if let Some(item) = SHARE_ITEM.get() {
        let _ = item.set_checked(checked);
    }
}

/// Restart the sidecar bound to loopback or all interfaces. Runs off the main
/// thread: stops, respawns, re-polls health, then reports.
fn restart_sidecar(handle: &AppHandle, shared: bool) {
    let handle = handle.clone();
    std::thread::spawn(move || {
        let state = handle.state::<ServerState>();
        let port = state.port;
        stop_sidecar(&state);
        match spawn_sidecar(port, shared) {
            Ok(child) => *state.child.lock().unwrap() = Some(child),
            Err(e) => {
                eprintln!("sidecar respawn failed: {e}");
                fail_and_exit(&handle);
                return;
            }
        }
        let deadline = Instant::now() + READY_TIMEOUT;
        while !health_ok(port) {
            if sidecar_died(&handle) || Instant::now() > deadline {
                fail_and_exit(&handle);
                return;
            }
            std::thread::sleep(Duration::from_millis(200));
        }
        *state.shared.lock().unwrap() = shared;
        let _ = std::fs::write(share_file(), if shared { "1" } else { "0" });
        set_share_checked(shared);
        if shared {
            let address = lan_ip()
                .map(|ip| format!("http://{ip}:{port}"))
                .unwrap_or_else(|| {
                    format!("http://<your-mac-ip>:{port} — find the IP in System Settings > Network")
                });
            info_dialog(
                &handle,
                &format!(
                    "Sharing on your network.\n\nTeammates connect at:\n{address}\n\nAn access key is required to sign in. macOS may ask to allow incoming connections — accept to share."
                ),
            );
        }
    });
}

fn toggle_share(handle: &AppHandle) {
    let state = handle.state::<ServerState>();
    let currently = *state.shared.lock().unwrap();
    if currently {
        restart_sidecar(handle, false);
        return;
    }
    // Never open an un-keyed board to the network.
    if !auth_enabled(state.port) {
        set_share_checked(false);
        if let Some(window) = handle.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
        }
        info_dialog(
            handle,
            "Set an access key first.\n\nSharing opens TodoScope to everyone on your network. Create a key on the TodoScope page (security banner), then turn sharing on again.",
        );
        return;
    }
    restart_sidecar(handle, true);
}

fn build_tray(app: &tauri::App) -> tauri::Result<()> {
    let open = MenuItemBuilder::with_id("open", "Open TodoScope").build(app)?;
    let share = CheckMenuItemBuilder::with_id("share_toggle", "Share on Network")
        .checked(*app.state::<ServerState>().shared.lock().unwrap())
        .build(app)?;
    let quit = MenuItemBuilder::with_id("quit", "Quit TodoScope").build(app)?;
    let menu = MenuBuilder::new(app).items(&[&open, &share, &quit]).build()?;
    let _ = SHARE_ITEM.set(share);
    let icon = tauri::image::Image::from_bytes(include_bytes!(
        "../../assets/todoscope_menu_icon.png"
    ))?;
    TrayIconBuilder::new()
        .icon(icon)
        .icon_as_template(true)
        .menu(&menu)
        .on_menu_event(|app, event| handle_menu_event(app, event.id().as_ref()))
        .build(app)?;
    Ok(())
}

/// macOS routes Cmd-key shortcuts through menu accelerators, so browser-style
/// zoom needs a real View menu. A custom menu replaces the default one, so the
/// App and Edit menus (quit, copy/paste) are re-declared here.
fn build_app_menu(app: &tauri::App) -> tauri::Result<()> {
    let app_menu = SubmenuBuilder::new(app, "TodoScope")
        .about(None)
        .separator()
        .hide()
        .hide_others()
        .show_all()
        .separator()
        .quit()
        .build()?;
    let edit = SubmenuBuilder::new(app, "Edit")
        .undo()
        .redo()
        .separator()
        .cut()
        .copy()
        .paste()
        .select_all()
        .build()?;
    let zoom_in = MenuItemBuilder::with_id("zoom_in", "Zoom In")
        .accelerator("CmdOrCtrl+=")
        .build(app)?;
    let zoom_out = MenuItemBuilder::with_id("zoom_out", "Zoom Out")
        .accelerator("CmdOrCtrl+-")
        .build(app)?;
    let zoom_reset = MenuItemBuilder::with_id("zoom_reset", "Actual Size")
        .accelerator("CmdOrCtrl+0")
        .build(app)?;
    let view = SubmenuBuilder::new(app, "View")
        .items(&[&zoom_in, &zoom_out, &zoom_reset])
        .build()?;
    let menu = MenuBuilder::new(app)
        .items(&[&app_menu, &edit, &view])
        .build()?;
    app.set_menu(menu)?;
    Ok(())
}

fn handle_menu_event(app: &AppHandle, id: &str) {
    match id {
        "open" => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            } else {
                let port = app.state::<ServerState>().port;
                open_main_window(app, port);
            }
        }
        "share_toggle" => toggle_share(app),
        "zoom_in" => zoom_by(app, |z| z * ZOOM_STEP),
        "zoom_out" => zoom_by(app, |z| z / ZOOM_STEP),
        "zoom_reset" => zoom_by(app, |_| 1.0),
        "quit" => app.exit(0),
        _ => {}
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .on_menu_event(|app, event| handle_menu_event(app, event.id().as_ref()))
        .setup(|app| {
            #[cfg(target_os = "macos")]
            if MENU_BAR_ONLY {
                app.set_activation_policy(tauri::ActivationPolicy::Accessory);
            }

            let shared = saved_share();
            // TODOSCOPE_DEV_PORT: attach to an externally run dev server, spawn nothing.
            let (port, child, spawn_failed) = match std::env::var("TODOSCOPE_DEV_PORT") {
                Ok(p) => (
                    p.parse::<u16>().expect("TODOSCOPE_DEV_PORT must be a port"),
                    None,
                    false,
                ),
                Err(_) => {
                    let port = pick_port();
                    match spawn_sidecar(port, shared) {
                        Ok(child) => (port, Some(child), false),
                        Err(e) => {
                            eprintln!("sidecar spawn failed: {e}");
                            (port, None, true) // readiness poll surfaces the dialog
                        }
                    }
                }
            };
            app.manage(ServerState {
                child: Mutex::new(child),
                port,
                spawn_failed,
                shared: Mutex::new(shared),
                zoom: Mutex::new(saved_zoom()),
            });

            build_app_menu(app)?;
            build_tray(app)?;

            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let deadline = Instant::now() + READY_TIMEOUT;
                loop {
                    if health_ok(port) {
                        break;
                    }
                    let state = handle.state::<ServerState>();
                    if state.spawn_failed || sidecar_died(&handle) || Instant::now() > deadline {
                        fail_and_exit(&handle);
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(200));
                }
                // A key may have been removed since sharing was enabled — never
                // stay open to the network without one.
                if *handle.state::<ServerState>().shared.lock().unwrap() && !auth_enabled(port) {
                    restart_sidecar(&handle, false);
                    info_dialog(
                        &handle,
                        "Network sharing was turned off: no access key is set. Create a key, then turn sharing on again from the menu bar icon.",
                    );
                }
                let main_handle = handle.clone();
                let _ = handle.run_on_main_thread(move || {
                    open_main_window(&main_handle, port);
                });
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri app")
        .run(|app, event| match event {
            RunEvent::ExitRequested { code, api, .. } => {
                if MENU_BAR_ONLY && code.is_none() {
                    // Last window closed: stay resident in the menu bar.
                    api.prevent_exit();
                }
            }
            RunEvent::Exit => stop_sidecar(&app.state::<ServerState>()),
            _ => {}
        });
}
