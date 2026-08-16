"""Last Scanned must resolve for repos whose display name differs from the folder.

Scan state is keyed by the directory basename. A repo registered under a
different display name used to miss that key and always report "never".
"""
import subprocess


def _make_repo(tmp_path, dirname):
    fix = tmp_path / dirname
    fix.mkdir()
    subprocess.run(['git', 'init', '-q', str(fix)], check=True)
    (fix / 'a.py').write_text('# TODO: hi\n')
    subprocess.run(['git', '-C', str(fix), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(fix), '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'i'], check=True)
    return fix


def test_last_scanned_resolves_when_display_name_differs(tmp_path, monkeypatch):
    monkeypatch.setenv('TODOSCOPE_DATA_DIR', str(tmp_path / 'data'))
    (tmp_path / 'data').mkdir()
    from scanner.app import app, save_local_repos, list_local_repositories

    # Folder is "demo-repo"; the user registers it as "Orchard".
    fix = _make_repo(tmp_path, 'demo-repo')
    save_local_repos({'Orchard': {'path': str(fix), 'public': False, 'webhook_secret': None}})
    app.config['TESTING'] = True
    client = app.test_client()

    rows = list_local_repositories()
    row = next(r for r in rows if r['name'] == 'Orchard')
    assert row['last_scanned_str'] is None, 'unscanned repo should report never'

    resp = client.get('/stream_data/Orchard')
    assert resp.status_code == 200
    assert 'complete' in resp.get_data(as_text=True)  # drives the generator to the state write

    rows = list_local_repositories()
    row = next(r for r in rows if r['name'] == 'Orchard')
    assert row['last_scanned_str'], 'scanned repo must show a timestamp, not never'
