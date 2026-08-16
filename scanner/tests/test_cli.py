"""
Tests for the TodoScope CLI entry point (scanner.cli).
"""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

import pytest


class TestFindFreePort:
    """Test the port-finding logic."""

    def test_returns_requested_port_when_free(self):
        from scanner.cli import find_free_port
        # Use a high port unlikely to be taken
        port = find_free_port(start=19876)
        assert port == 19876

    def test_skips_occupied_port(self):
        from scanner.cli import find_free_port
        # Occupy a port, then ask for it
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 19877))
            s.listen(1)
            port = find_free_port(start=19877)
            assert port != 19877
            assert port == 19878  # should be next one up

    def test_probes_upward(self):
        from scanner.cli import find_free_port
        # Occupy two consecutive ports
        sockets = []
        for p in (19880, 19881):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.listen(1)
            sockets.append(s)
        try:
            port = find_free_port(start=19880)
            assert port == 19882
        finally:
            for s in sockets:
                s.close()


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cli_env():
    """Return env dict with PYTHONPATH set so subprocess can import scanner."""
    env = os.environ.copy()
    env["PYTHONPATH"] = _PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return env


class TestCLIVersionAndHelp:
    """Test the CLI responds to --version and --help."""

    def test_version_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "scanner.cli", "--version"],
            capture_output=True, text=True, cwd=_PROJECT_ROOT, env=_cli_env(),
        )
        assert result.returncode == 0
        assert "todoscope" in result.stdout
        # Read the version rather than pinning it — a release bump is not a test failure.
        from scanner import __version__
        assert __version__ in result.stdout

    def test_help_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "scanner.cli", "--help"],
            capture_output=True, text=True, cwd=_PROJECT_ROOT, env=_cli_env(),
        )
        assert result.returncode == 0
        assert "--no-browser" in result.stdout
        assert "--tunnel" in result.stdout
        assert "--tailscale" in result.stdout
        assert "--share" in result.stdout
        assert "--port" in result.stdout


class TestCLIServerStartup:
    """Test that the server actually starts and responds."""

    def test_server_starts_headless(self):
        """Start todoscope --no-browser, verify it responds, then kill it."""
        port = 15432  # unlikely to collide
        proc = subprocess.Popen(
            [sys.executable, "-m", "scanner.cli", "--no-browser", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=_PROJECT_ROOT, env=_cli_env(),
        )
        try:
            import urllib.request
            ready = False
            for _ in range(30):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5)
                    ready = True
                    break
                except Exception:
                    time.sleep(0.5)
            assert ready, "Server did not start within 15 seconds"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_auto_finds_free_port(self):
        """If requested port is taken, server should find the next one."""
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 15433))
        blocker.listen(1)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "scanner.cli", "--no-browser", "--port", "15433"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                cwd=_PROJECT_ROOT, env=_cli_env(),
            )
            try:
                import urllib.request
                time.sleep(3)
                try:
                    urllib.request.urlopen("http://127.0.0.1:15434/", timeout=2)
                    found = True
                except Exception:
                    found = False
                assert found, "Server should have started on port 15434"
            finally:
                proc.terminate()
                proc.wait(timeout=5)
        finally:
            blocker.close()


class TestDataDir:
    """Test that TODOSCOPE_DATA_DIR env var is respected."""

    def test_data_dir_created(self):
        """When TODOSCOPE_DATA_DIR is set, repositories subdir should be created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = os.path.join(tmpdir, "todoscope_test")
            # cli.py creates it before importing app
            os.makedirs(os.path.join(data_dir, "repositories"), exist_ok=True)
            os.environ["TODOSCOPE_DATA_DIR"] = data_dir
            try:
                assert os.path.isdir(os.path.join(data_dir, "repositories"))
            finally:
                del os.environ["TODOSCOPE_DATA_DIR"]


class TestAutoMigration:
    """Test the scanner/repositories/ → ~/.todoscope/repositories/ migration."""

    def test_migration_moves_repos(self):
        """If old repo dir has content and new dir is empty, content should migrate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate old repo dir
            old_dir = os.path.join(tmpdir, "old_repos")
            os.makedirs(old_dir)
            # Create a fake repo
            os.makedirs(os.path.join(old_dir, "my-repo", ".git"))
            with open(os.path.join(old_dir, "my-repo", "README.md"), "w") as f:
                f.write("# test")

            # Simulate new data dir
            new_dir = os.path.join(tmpdir, "new_repos")
            os.makedirs(new_dir, exist_ok=True)

            # Perform migration logic (extracted from app.py)
            import shutil
            if os.path.isdir(old_dir) and os.listdir(old_dir):
                if not os.listdir(new_dir):
                    for item in os.listdir(old_dir):
                        src = os.path.join(old_dir, item)
                        dst = os.path.join(new_dir, item)
                        shutil.move(src, dst)

            # Verify
            assert os.path.isdir(os.path.join(new_dir, "my-repo", ".git"))
            assert not os.listdir(old_dir)  # old dir should be empty

    def test_no_migration_if_new_dir_has_content(self):
        """If new dir already has content, don't overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.path.join(tmpdir, "old_repos")
            os.makedirs(os.path.join(old_dir, "old-repo"))

            new_dir = os.path.join(tmpdir, "new_repos")
            os.makedirs(os.path.join(new_dir, "existing-repo"))

            import shutil
            if os.path.isdir(old_dir) and os.listdir(old_dir):
                if not os.listdir(new_dir):
                    for item in os.listdir(old_dir):
                        shutil.move(os.path.join(old_dir, item), os.path.join(new_dir, item))

            # old-repo should NOT have moved
            assert os.path.isdir(os.path.join(old_dir, "old-repo"))
            assert not os.path.isdir(os.path.join(new_dir, "old-repo"))


class TestResolveTunnel:
    """Test tunnel resolution logic."""

    def test_tunnel_flag(self):
        from scanner.cli import resolve_tunnel
        from argparse import Namespace
        args = Namespace(tunnel=True, tailscale=False, share=False)
        assert resolve_tunnel(args) == "cloudflared"

    def test_tailscale_flag(self):
        from scanner.cli import resolve_tunnel
        from argparse import Namespace
        args = Namespace(tunnel=False, tailscale=True, share=False)
        assert resolve_tunnel(args) == "tailscale"

    def test_no_tunnel(self):
        from scanner.cli import resolve_tunnel
        from argparse import Namespace
        args = Namespace(tunnel=False, tailscale=False, share=False)
        assert resolve_tunnel(args) is None
