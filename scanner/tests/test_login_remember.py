"""Remember-me: the session cookie gains an expiry only when asked."""

import csv

import pytest


@pytest.fixture
def keyed_client(tmp_path, monkeypatch):
    import scanner.app as app_module
    keys_file = tmp_path / 'access_keys.csv'
    with open(keys_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['key'])
        writer.writeheader()
        writer.writerow({'key': 'sekrit'})
    monkeypatch.setattr(app_module, 'ACCESS_KEYS_FILE', str(keys_file))
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _login_cookie(resp):
    for header in resp.headers.getlist('Set-Cookie'):
        if header.startswith('session='):
            return header
    return None


def test_remember_sets_persistent_cookie(keyed_client):
    resp = keyed_client.post('/login', data={'key': 'sekrit', 'remember': 'on'})
    assert resp.status_code == 302
    cookie = _login_cookie(resp)
    assert cookie is not None
    assert 'Expires=' in cookie  # persistent, survives browser/app restart


def test_no_remember_sets_session_cookie(keyed_client):
    resp = keyed_client.post('/login', data={'key': 'sekrit'})
    assert resp.status_code == 302
    cookie = _login_cookie(resp)
    assert cookie is not None
    assert 'Expires=' not in cookie  # plain session cookie


def test_bad_key_still_rejected(keyed_client):
    resp = keyed_client.post('/login', data={'key': 'wrong', 'remember': 'on'})
    assert resp.status_code == 200
    assert b'Invalid key' in resp.data
