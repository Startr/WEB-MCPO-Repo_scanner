# Platypus + Homebrew Distribution

> Research notes — 2026-04-21

## Platypus Overview

[Platypus](https://sveinbjorn.org/platypus) wraps command-line scripts/binaries
into native macOS .app bundles. v5.5.0 (Dec 2025), requires macOS 11+,
Universal Intel/ARM binary, Apple notarized.

Install: `brew install --cask platypus`

### Interface Types (pick one per app)

| Type          | Use Case                                              |
|---------------|-------------------------------------------------------|
| **None**      | Windowless background app (output to stderr)          |
| **Progress Bar** | Shows progress + cancel button                    |
| **Text Window**  | Scrollable text output (not a full terminal)       |
| **Web View**     | **WebKit HTML rendering** — can show a full web UI |
| **Status Menu**  | Menu bar item                                      |
| **Droplet**      | Drag-and-drop file processing                      |

**For repo_scanner**: "Web View" or "Status Menu" make the most sense.
- **Web View**: Platypus launches the Flask server, then renders
  `http://localhost:5000` in a native WebKit window. Feels like a real Mac app.
- **Status Menu**: Menu bar icon, click to open in default browser. Lighter.

### Bundled Files

Platypus copies files into the app's `Resources/` folder. The script can
access them at runtime. For our case, we'd bundle:
- The PyInstaller `--onedir` output (Python + Flask + deps)
- Or a `py-app-standalone` directory
- The `scanner/` templates and static files (if not already in the binary)

CLI flag: `-f path/to/file` (repeat for multiple files)

### Command Line Tool

```bash
# Install CLI (from Platypus.app → Settings → Install)
# Creates /usr/local/bin/platypus

# Build from profile
/usr/local/bin/platypus -P RepoScanner.platypus "RepoScanner.app"

# Build from flags
/usr/local/bin/platypus \
    -a "RepoScanner"           \  # App name
    -o "Web"                   \  # Interface type (Web View)
    -i icon.icns               \  # App icon
    -V "1.0.0"                 \  # Version
    -u "Sage.is"               \  # Author
    -f dist/repo_scanner/      \  # Bundle the PyInstaller output dir
    launch.sh                  \  # The script to run
    "RepoScanner.app"             # Output path
```

### The Launch Script (what Platypus actually runs)

For Web View mode, the script's stdout is rendered as HTML. But for our use
case, we want to launch the Flask server and point WebKit at it:

```bash
#!/bin/bash
# launch.sh — Platypus entry point for RepoScanner

DIR="$(dirname "$0")"
RESOURCES="$DIR/../Resources"

# Start the Flask server in background
"$RESOURCES/repo_scanner/repo_scanner" &
SERVER_PID=$!

# Wait for it to be ready
for i in $(seq 1 30); do
    curl -s http://localhost:5000/ > /dev/null && break
    sleep 0.5
done

# Tell Platypus Web View to load
echo "Location: http://localhost:5000/"

# Cleanup on exit
trap "kill $SERVER_PID 2>/dev/null" EXIT
wait $SERVER_PID
```

### Profile Files (.platypus)

XML plist format. Save from the GUI, then use in CI:
```bash
/usr/local/bin/platypus -P RepoScanner.platypus dist/RepoScanner.app
```

This means we can automate .app creation in our release pipeline.

---

## Homebrew Distribution

We have two paths into Homebrew from `homebrew-apps`:

### Path A: Formula (CLI tool)

Like the existing `ai-ui` pattern. Ships a wrapper script that manages Docker.

```ruby
# Formula/repo-scanner.rb
class RepoScanner < Formula
  desc "Scan Git repos for TODOs, generate kanban boards"
  homepage "https://github.com/Sage-is/repo_scanner"
  url "https://github.com/Sage-is/repo_scanner/archive/refs/tags/v#{version}.tar.gz"
  sha256 "abc123..."

  depends_on "docker"
  depends_on "git"

  def install
    bin.install "repo-scanner"   # wrapper script
  end

  def caveats
    <<~EOS
      Start RepoScanner:
        repo-scanner start

      Open in browser:
        repo-scanner open

      Stop:
        repo-scanner stop
    EOS
  end

  test do
    assert_match "RepoScanner", shell_output("#{bin}/repo-scanner --version")
  end
end
```

**Install**: `brew install sage-is/apps/repo-scanner`

This needs a `repo-scanner` CLI wrapper script (like `ai-ui` — manages
Docker container lifecycle: start/stop/update/logs/dev/nuke).

### Path B: Cask (Mac .app)

For distributing the Platypus-generated .app bundle.

```ruby
# Casks/repo-scanner.rb
cask "repo-scanner" do
  version "1.0.0"
  sha256 "def456..."

  url "https://github.com/Sage-is/repo_scanner/releases/download/v#{version}/RepoScanner-#{version}.dmg"
  name "RepoScanner"
  desc "Scan Git repos for TODOs, generate kanban boards"
  homepage "https://github.com/Sage-is/repo_scanner"

  depends_on macos: ">= :big_sur"

  app "RepoScanner.app"

  zap trash: [
    "~/.repo-scanner",
    "~/Library/Application Support/RepoScanner",
  ]
end
```

**Install**: `brew install --cask sage-is/apps/repo-scanner`

**Packaging**: Need to create a .dmg containing the .app for download.
GitHub Releases hosts the .dmg artifact.

### Cask in a Custom Tap

Homebrew supports casks in custom taps. Structure:
```
homebrew-apps/
├── Formula/
│   └── repo-scanner.rb      # CLI formula (Docker wrapper)
├── Casks/
│   └── repo-scanner.rb      # .app cask
```

Users choose:
- `brew install sage-is/apps/repo-scanner` → CLI/Docker wrapper
- `brew install --cask sage-is/apps/repo-scanner` → native Mac .app

---

## UPDATE: pywebview + pystray (replaces Platypus for .app)

Platypus cannot combine Status Menu + Web View in a single app — they are mutually
exclusive. The solution is **pure Python**:

- **pywebview** — native WKWebView window on macOS (<10MB, <500ms startup)
- **pystray** — native NSStatusItem (menu bar icon) on macOS
- pywebview has an **official pystray example** at:
  https://pywebview.flowrl.com/examples/pystray_icon
- Both bundle with PyInstaller
- macOS requires `multiprocessing.set_start_method("spawn")` for compatibility
- `icon.run_detached()` lets pywebview own the main thread (required on macOS)

This gives us: 🔭 status bar icon + WKWebView window + SSE streaming — all pure Python.

---

## Recommended Approach for repo_scanner

### Tier 1: Docker CLI via Brew (fastest to ship)
- Write a `repo-scanner` CLI wrapper (bash, ~300 lines, based on ai-ui)
- Add formula to homebrew-apps
- Follows existing proven pattern

### Tier 2: Standalone binary
- Add pyproject.toml to repo_scanner
- PyInstaller `--onedir` build → produces `dist/repo_scanner/`
- GitHub Actions builds on macOS runner, attaches to release
- Users download and run `./repo_scanner` directly

### Tier 3: Mac .app via Platypus + Brew Cask
- Platypus wraps the PyInstaller onedir output into .app
- Package into .dmg
- GitHub Actions attaches .dmg to release
- Add cask to homebrew-apps
- Most polished user experience

### Tier 4: PyPI / uv tool install
- Add pyproject.toml with `[project.scripts]` entry point
- Publish to PyPI
- `uv tool install repo-scanner` or `pipx install repo-scanner`
- For Python developers

---

## Key Decisions Needed

1. **App name**: `RepoScanner`? `TodoScope`? (brand alignment)
2. **Icon**: Need an .icns file for the .app bundle
3. **Port conflict handling**: What if 5000 is already in use?
4. **Data directory**: Where does the .app store cloned repos?
   (`~/Library/Application Support/RepoScanner/repositories/`?)
5. **Auto-open browser**: CLI binary should auto-open browser on start?
6. **Menubar vs window**: Status Menu item or WebKit window for .app?

Sources:
- https://github.com/sveinbjornt/Platypus
- https://sveinbjorn.org/platypus
- https://docs.brew.sh/Cask-Cookbook
- https://docs.brew.sh/Adding-Software-to-Homebrew
