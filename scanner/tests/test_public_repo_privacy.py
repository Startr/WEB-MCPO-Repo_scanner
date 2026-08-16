"""Public local repos must not leak the server's filesystem path.

The scan-stream init payload carries local_path for local-editor deep links.
Only authed viewers may see it; anonymous viewers of a public repo get the
same stream minus the path.
"""
import json
import os
import subprocess


def _make_repo(tmp_path):
    fix = tmp_path / 'fixrepo'
    fix.mkdir()
    subprocess.run(['git', 'init', '-q', str(fix)], check=True)
    (fix / 'a.py').write_text('# TODO: hi\n')
    subprocess.run(['git', '-C', str(fix), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(fix), '-c', 'user.email=t@t', '-c', 'user.name=t',
                    'commit', '-qm', 'i'], check=True)
    return fix


def _init_event(resp):
    for line in resp.get_data(as_text=True).splitlines():
        if line.startswith('data: '):
            evt = json.loads(line[len('data: '):])
            if evt.get('type') == 'init':
                return evt
    return None


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv('TODOSCOPE_DATA_DIR', str(tmp_path / 'data'))
    (tmp_path / 'data').mkdir()
    from scanner.app import app, ACCESS_KEYS_FILE, save_local_repos
    with open(ACCESS_KEYS_FILE, 'w') as f:
        f.write('key,label\nsecret123,test\n')
    fix = _make_repo(tmp_path)
    save_local_repos({'fixrepo': {'path': str(fix), 'public': True, 'webhook_secret': None}})
    app.config['TESTING'] = True
    return app


def test_anonymous_public_stream_has_no_local_path(tmp_path, monkeypatch):
    app = _setup(tmp_path, monkeypatch)
    client = app.test_client()
    resp = client.get('/stream_data/fixrepo')
    assert resp.status_code == 200
    init = _init_event(resp)
    assert init is not None
    assert 'local_path' not in init


def test_authed_stream_keeps_local_path(tmp_path, monkeypatch):
    app = _setup(tmp_path, monkeypatch)
    client = app.test_client()
    with client.session_transaction() as s:
        s['authed_key'] = 'secret123'
    resp = client.get('/stream_data/fixrepo')
    assert resp.status_code == 200
    init = _init_event(resp)
    assert init is not None
    assert init.get('local_path', '').endswith('fixrepo')
