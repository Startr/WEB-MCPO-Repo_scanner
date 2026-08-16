"""Live change feed — the server's ears.

Registered local repos get a filesystem watcher (watchdog); cloned repos get
a relaxed git poll. Both funnel into the same pipeline: incremental rescan →
render HTML fragments → publish to every subscribed SSE client.

Watchers are lazy: started when the first client subscribes to a repo,
stopped when the last one leaves. The scanner's own writes (KANBAN.canvas)
are ignored so a rescan never triggers itself.
"""

import os
import subprocess
import threading
import time
from queue import Queue, Empty, Full

__all__ = ['subscribe', 'unsubscribe', 'publish', 'notify_change', 'Empty']

DEBOUNCE_SECONDS = 0.4
LOCAL_FALLBACK_POLL_SECONDS = 2    # watchdog unavailable → coarse fingerprint poll
REMOTE_POLL_SECONDS = 60
IGNORE_BASENAMES = {'KANBAN.canvas', 'KANBAN.canvas.tmp'}

_lock = threading.Lock()
_subscribers = {}    # repo_name -> set of Queue
_watchers = {}       # repo_name -> _Handle
_rescan_locks = {}   # repo_name -> Lock


def subscribe(repo_name, repo_path, is_local):
    """Register an SSE client; starts the repo's watcher if it's the first."""
    q = Queue(maxsize=100)
    with _lock:
        _subscribers.setdefault(repo_name, set()).add(q)
        if repo_name not in _watchers:
            _watchers[repo_name] = _start_watcher(repo_name, repo_path, is_local)
    return q


def unsubscribe(repo_name, q):
    """Drop an SSE client; stops the repo's watcher if it was the last."""
    handle = None
    with _lock:
        subs = _subscribers.get(repo_name)
        if subs is not None:
            subs.discard(q)
            if not subs:
                _subscribers.pop(repo_name, None)
                handle = _watchers.pop(repo_name, None)
    if handle:
        handle.stop()


def publish(repo_name, event):
    """Fan an event dict out to every subscriber of a repo."""
    with _lock:
        queues = list(_subscribers.get(repo_name, ()))
    for q in queues:
        try:
            q.put_nowait(event)
        except Full:
            pass  # slow client — it will resync on its next full fragment


def notify_change(repo_name):
    """External change signal (e.g. webhook) — rescan and publish if anyone
    is listening."""
    with _lock:
        active = repo_name in _subscribers and bool(_subscribers[repo_name])
    if not active:
        return
    from .app import resolve_repo_path
    repo_path = resolve_repo_path(repo_name)
    if repo_path:
        threading.Thread(target=_rescan_and_publish, args=(repo_name, repo_path),
                         daemon=True, name=f'live-webhook-{repo_name}').start()


class _Handle:
    def __init__(self, stop_fn):
        self._stop_fn = stop_fn

    def stop(self):
        try:
            self._stop_fn()
        except Exception:
            pass


def _relevant(path):
    if not path:
        return False
    parts = path.split(os.sep)
    if '.git' in parts:
        return False
    return os.path.basename(path) not in IGNORE_BASENAMES


def _start_watcher(repo_name, repo_path, is_local):
    if is_local:
        try:
            return _start_watchdog(repo_name, repo_path)
        except Exception as e:
            from .app import app
            app.logger.warning(f"watchdog unavailable for {repo_name} ({e}); falling back to poll")
            return _start_poller(repo_name, repo_path,
                                 LOCAL_FALLBACK_POLL_SECONDS, remote=False)
    return _start_poller(repo_name, repo_path, REMOTE_POLL_SECONDS, remote=True)


def _start_watchdog(repo_name, repo_path):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    pending = threading.Event()
    stop = threading.Event()

    class _Changed(FileSystemEventHandler):
        def on_any_event(self, event):
            if getattr(event, 'is_directory', False):
                return
            if _relevant(getattr(event, 'src_path', None)) or \
               _relevant(getattr(event, 'dest_path', None)):
                pending.set()

    observer = Observer()
    observer.daemon = True
    observer.schedule(_Changed(), repo_path, recursive=True)
    observer.start()

    def loop():
        while not stop.is_set():
            if pending.wait(timeout=0.5):
                time.sleep(DEBOUNCE_SECONDS)   # let the save-burst settle
                pending.clear()
                if not stop.is_set():
                    _rescan_and_publish(repo_name, repo_path)

    threading.Thread(target=loop, daemon=True, name=f'live-debounce-{repo_name}').start()

    def stop_fn():
        stop.set()
        pending.set()   # unblock the debounce loop so it can exit
        observer.stop()
    return _Handle(stop_fn)


def _git(repo_path, *args, timeout=30):
    return subprocess.run(['git', '-C', repo_path, *args],
                          capture_output=True, text=True, timeout=timeout)


def _local_fingerprint(repo_path):
    try:
        head = _git(repo_path, 'rev-parse', 'HEAD', timeout=5).stdout.strip()
        status = _git(repo_path, 'status', '--porcelain=v1', timeout=10).stdout
        status = '\n'.join(l for l in status.splitlines()
                           if _relevant(l[3:] if len(l) > 3 else ''))
        return head + '\n' + status
    except Exception:
        return None


def _start_poller(repo_name, repo_path, interval, remote):
    stop = threading.Event()

    def loop():
        from .app import app, pull_repository
        last_fp = None if remote else _local_fingerprint(repo_path)
        while not stop.wait(interval):
            try:
                if remote:
                    _git(repo_path, 'fetch', '--quiet', timeout=60)
                    local = _git(repo_path, 'rev-parse', 'HEAD', timeout=5).stdout.strip()
                    upstream = _git(repo_path, 'rev-parse', '@{u}', timeout=5).stdout.strip()
                    if upstream and local and local != upstream:
                        pull_repository(repo_path)
                        _rescan_and_publish(repo_name, repo_path)
                else:
                    fp = _local_fingerprint(repo_path)
                    if fp is not None and fp != last_fp:
                        last_fp = fp
                        _rescan_and_publish(repo_name, repo_path)
            except Exception as e:
                app.logger.warning(f"live poll failed for {repo_name}: {e}")

    threading.Thread(target=loop, daemon=True, name=f'live-poll-{repo_name}').start()
    return _Handle(stop.set)


def _repo_lock(repo_name):
    with _lock:
        return _rescan_locks.setdefault(repo_name, threading.Lock())


def _rescan_and_publish(repo_name, repo_path):
    """Incremental rescan → fragments → publish. Serialized per repo."""
    from .app import (app, load_exclusions, find_todo_files, find_todos,
                      load_scan_state, save_scan_state, _git_head_sha,
                      exclusions_hash, git_changed_paths, rescan_files,
                      collect_blame_data, TodoItem, SCAN_STATE_SCHEMA)
    from .kanban import build_kanban, write_canvas
    from . import fragments
    from datetime import datetime

    lock = _repo_lock(repo_name)
    if not lock.acquire(blocking=False):
        return  # a rescan is already running; the watcher will re-fire if needed
    try:
        with app.app_context():
            exclusions = load_exclusions(repo_path)
            todo_md_files = find_todo_files(repo_path, exclusions=exclusions)
            state = load_scan_state(repo_name)
            current_head = _git_head_sha(repo_path)
            exc_hash = exclusions_hash(exclusions)

            todos_collected = []
            changed = None
            if state and state.get('last_head') and state.get('exclusions_hash') == exc_hash:
                changed, deleted = git_changed_paths(repo_path, state['last_head'])
            if changed is not None:
                cached_todos = dict(state.get('todos') or {})
                for path in deleted:
                    cached_todos.pop(path, None)
                cached_todos.update(rescan_files(repo_path, changed, exclusions))
                for rel_path, items in cached_todos.items():
                    for item in items:
                        todos_collected.append(TodoItem(
                            rel_path, item['line_num'], item['todo_text'], item['next_line']))
            else:
                todos_collected = list(find_todos(repo_path, exclusions=exclusions))

            canvas, cards = build_kanban(todo_md_files, todos_collected)
            write_canvas(repo_path, canvas)
            blame_data = collect_blame_data(repo_path, cards)

            if current_head:
                todos_by_file = {}
                for t in todos_collected:
                    todos_by_file.setdefault(t.file_path, []).append({
                        'line_num': t.line_num,
                        'todo_text': t.todo_text,
                        'next_line': t.next_line,
                    })
                save_scan_state(repo_name, {
                    'schema': SCAN_STATE_SCHEMA,
                    'last_head': current_head,
                    'exclusions_hash': exc_hash,
                    'scanned_at': datetime.utcnow().isoformat() + 'Z',
                    'todos': todos_by_file,
                    'blame': blame_data or {},
                })

            todo_dicts = [t.to_dict() for t in todos_collected]
            md_sources = {f['file_path']: f['content'] for f in todo_md_files if f.get('content')}
            publish(repo_name, {
                'type': 'kanban',
                'html': fragments.render_kanban_html(canvas, blame_data, md_sources=md_sources),
            })
            publish(repo_name, {
                'type': 'todo_md_files',
                'count': len(todo_md_files),
                'html': fragments.render_todo_md_files_html(todo_md_files),
            })
            publish(repo_name, {
                'type': 'todos_list',
                'count': len(todo_dicts),
                'html': fragments.render_todos_list_html(todo_dicts, blame_data),
            })
    except Exception as e:
        from .app import app as _app
        _app.logger.error(f"live rescan failed for {repo_name}: {e}")
    finally:
        lock.release()
