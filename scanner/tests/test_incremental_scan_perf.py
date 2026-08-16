"""Scaled benchmark: incremental scans must beat full scans.

Builds a 400-file repo (25 carry TODOs), then times three stream passes with
timeit: cold full scan, one-file incremental, and the no-change cached path.
The speed assertions are deliberately loose (2x) — the real ratio is ~10x+ —
so the test stays green on slow CI while still catching a broken incremental
branch that silently falls back to full scans.
"""
import json
import subprocess
import timeit

N_FILES = 400
N_TODO_FILES = 25


def _git(repo, *args):
    subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@t', '-c', 'user.name=t',
                    *args], check=True, capture_output=True)


def _make_repo(tmp_path):
    fix = tmp_path / 'bigrepo'
    fix.mkdir()
    subprocess.run(['git', 'init', '-q', str(fix)], check=True)
    for i in range(N_FILES):
        sub = fix / f'pkg{i % 20}'
        sub.mkdir(exist_ok=True)
        body = f'def f{i}():\n    return {i}\n'
        if i < N_TODO_FILES:
            body += f'# TODO: item-{i}\n'
        (sub / f'mod{i}.py').write_text(body)
    _git(fix, 'add', '.')
    _git(fix, 'commit', '-qm', 'init')
    return fix


def _stream(client):
    resp = client.get('/stream_data/bigrepo')
    assert resp.status_code == 200
    events = [json.loads(l[len('data: '):])
              for l in resp.get_data(as_text=True).splitlines() if l.startswith('data: ')]
    statuses = [e['message'] for e in events if e['type'] == 'status']
    complete = next(e for e in events if e['type'] == 'complete')
    return statuses, complete


def test_incremental_beats_full_scan_at_scale(tmp_path, monkeypatch):
    monkeypatch.setenv('TODOSCOPE_DATA_DIR', str(tmp_path / 'data'))
    (tmp_path / 'data').mkdir()
    from scanner.app import app, save_local_repos
    fix = _make_repo(tmp_path)
    save_local_repos({'bigrepo': {'path': str(fix), 'public': False, 'webhook_secret': None}})
    app.config['TESTING'] = True
    client = app.test_client()

    results = {}

    def timed(label):
        out = {}
        def run():
            out['statuses'], out['complete'] = _stream(client)
        seconds = timeit.timeit(run, number=1)
        results[label] = (seconds, out['statuses'], out['complete'])
        return seconds, out['statuses'], out['complete']

    # Pass 1: cold — no scan state — must take the full-scan branch.
    t_full, st_full, done_full = timed('full')
    assert any(m.startswith('Scanning code') for m in st_full), st_full
    assert done_full['count'] == N_TODO_FILES

    # One-file change: append a TODO, commit.
    target = fix / 'pkg0' / 'mod0.py'
    target.write_text(target.read_text() + '# TODO: appended\n')
    _git(fix, 'add', '.')
    _git(fix, 'commit', '-qm', 'edit one file')

    # Pass 2: incremental — re-parses one file, serves the rest from state.
    t_inc, st_inc, done_inc = timed('incremental')
    assert any(m.startswith('Incremental scan — 1 file(s)') for m in st_inc), st_inc
    assert done_inc['count'] == N_TODO_FILES + 1

    # Pass 3: untouched repo — the no-change law: cached, zero scanning.
    t_cached, st_cached, done_cached = timed('cached')
    assert any(m.startswith('No changes since last scan') for m in st_cached), st_cached
    assert done_cached['count'] == N_TODO_FILES + 1

    print(f"\n{N_FILES} files: full={t_full:.2f}s "
          f"incremental={t_inc:.2f}s ({t_full / t_inc:.1f}x) "
          f"cached={t_cached:.2f}s ({t_full / t_cached:.1f}x)")

    assert t_inc < t_full * 0.5, f"incremental not faster: {t_inc:.2f}s vs full {t_full:.2f}s"
    assert t_cached < t_full * 0.5, f"cached not faster: {t_cached:.2f}s vs full {t_full:.2f}s"
