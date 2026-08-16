"""Tests for the /health readiness probe used by the desktop shell."""

import csv
import os

import pytest


@pytest.fixture
def client():
    from scanner.app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_health_ok(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['app'] == 'todoscope'
    assert isinstance(data['auth'], bool)  # actual value depends on access_keys.csv presence
    from scanner import __version__
    assert data['version'] == __version__


def test_health_public_with_auth_enabled(client, tmp_path, monkeypatch):
    """Stays 200 without credentials even when access keys gate the app."""
    import scanner.app as app_module
    keys_file = tmp_path / 'access_keys.csv'
    with open(keys_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['key'])
        writer.writeheader()
        writer.writerow({'key': 'sekrit'})
    monkeypatch.setattr(app_module, 'ACCESS_KEYS_FILE', str(keys_file))

    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['auth'] is True  # keys exist, so the shell may allow sharing

    # sanity: the gate itself works — an authed route redirects to /login
    gated = client.get('/', headers={'Accept': 'text/html'})
    assert gated.status_code == 302
    assert '/login' in gated.headers['Location']


def test_secret_key_persists(tmp_path, monkeypatch):
    """With a data dir and no SECRET_KEY env, the generated key is reused."""
    import scanner.app as app_module
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setattr(app_module, '_DATA_DIR', str(tmp_path))

    first = app_module._load_secret_key()
    second = app_module._load_secret_key()
    assert first == second
    key_path = tmp_path / '.secret_key'
    assert key_path.exists()
    assert (os.stat(key_path).st_mode & 0o777) == 0o600
