"""Basic tests for the todoscope CLI wrapper script."""

import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "scripts", "todoscope"
)
SCRIPT = os.path.normpath(SCRIPT)


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run the todoscope script with given arguments."""
    return subprocess.run(
        [SCRIPT] + args,
        capture_output=True,
        text=True,
        timeout=10,
        **kwargs,
    )


class TestHelp:
    """Verify --help / help output."""

    @pytest.mark.parametrize("flag", ["--help", "-h", "help"])
    def test_help_exits_zero(self, flag):
        result = _run([flag])
        assert result.returncode == 0

    def test_help_shows_usage(self):
        result = _run(["--help"])
        assert "Usage: todoscope" in result.stdout

    def test_no_args_shows_usage(self):
        result = _run([])
        assert "Usage: todoscope" in result.stdout
        assert result.returncode == 0

    def test_help_lists_commands(self):
        result = _run(["--help"])
        for cmd in ("start", "stop", "update", "dev", "logs", "open",
                     "status", "version", "tunnel", "tailscale", "nuke"):
            assert cmd in result.stdout, f"Expected '{cmd}' in help output"


class TestVersion:
    """Verify version output."""

    @pytest.mark.parametrize("flag", ["version", "--version", "-v"])
    def test_version_exits_zero(self, flag):
        result = _run([flag])
        assert result.returncode == 0

    def test_version_format(self):
        result = _run(["version"])
        assert result.stdout.startswith("todoscope ")
        # Version should look like X.Y.Z
        version_str = result.stdout.strip().split(" ", 1)[1]
        parts = version_str.split(".")
        assert len(parts) == 3, f"Expected semver, got '{version_str}'"
        for part in parts:
            assert part.isdigit(), f"Non-numeric version part: '{part}'"


class TestUnknownCommand:
    """Verify unknown commands produce an error."""

    def test_unknown_command_nonzero(self):
        result = _run(["doesnotexist"])
        assert result.returncode != 0

    def test_unknown_command_message(self):
        result = _run(["doesnotexist"])
        assert "Unknown command" in result.stdout or "Unknown command" in result.stderr
