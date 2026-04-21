# Packaging Options for repo_scanner

> Research notes — 2026-04-21

## The Problem

New Macs (M1+, macOS 12.3+) no longer ship with Python. Users who want to run
repo_scanner without Docker currently need to install Python + Pipenv themselves.
We need distribution channels that work without a pre-existing Python install.

## Current State

- **Deps**: Flask 3.1.0, PyYAML — that's it (2 direct, ~8 total)
- **All pure Python** — zero C extensions, zero native bindings
- **System deps**: `git` (subprocess), `file` command (MIME detection)
- **Code size**: ~100KB Python, ~164KB static/templates
- **Entry point**: `app.py` → Flask on 0.0.0.0:5000
- **No pyproject.toml or setup.py yet** — not packaged for PyPI

---

## Option 1: PyInstaller (Recommended for Binary)

**What it does**: Freezes Python interpreter + deps + code into a single binary.

**Key commands**:
```bash
# Basic onefile build
pyinstaller -F \
    --add-data "scanner/templates:scanner/templates" \
    --add-data "scanner/static:scanner/static" \
    app.py

# With hidden imports (if needed)
pyinstaller -F \
    --hidden-import=yaml \
    --add-data "scanner/templates:scanner/templates" \
    --add-data "scanner/static:scanner/static" \
    app.py
```

**Flask-specific gotcha — sys._MEIPASS**:
When frozen, Flask can't find templates/static in the usual location. Need:
```python
import sys, os
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'scanner', 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'scanner', 'static')
else:
    template_folder = 'scanner/templates'
    static_folder = 'scanner/static'
```

**Pros**:
- Mature, battle-tested (most popular Python packaging tool)
- Pure Python deps = easy bundling, no C compilation needed
- Produces universal binary if built on macOS with `--target-arch universal2`
- ~25-50MB expected binary size for our lean Flask app
- GitHub Actions can build per-platform in CI

**Cons**:
- Cannot cross-compile (must build on macOS for macOS)
- `--onefile` on macOS not recommended for notarized/sandboxed apps
  (use `--onedir` for .app bundles instead)
- Startup: onefile must extract to temp dir each launch (~1-3s)
- Build needs Python installed on the build machine

**Verdict**: Best choice for CLI binary. Use `--onedir` mode when wrapping
into a .app bundle via Platypus.

Sources:
- https://pyinstaller.org/en/stable/usage.html
- https://til.simonwillison.net/python/packaging-pyinstaller
- https://elc.github.io/posts/executable-flask-pyinstaller/

---

## Option 2: Nuitka (Alternative Compiler)

**What it does**: Transpiles Python → C → native machine code. Not a freezer —
an actual compiler. Uses libpython at runtime but code runs as compiled C.

**Key commands**:
```bash
# Standalone (directory)
python -m nuitka --mode=standalone app.py

# Onefile
python -m nuitka --mode=onefile app.py
```

**Pros**:
- 2-4x faster execution than CPython
- 2-3x faster startup than PyInstaller
- Supports Python 3.4–3.14
- True compilation = harder to reverse-engineer

**Cons**:
- macOS support is "worse" (their words) — pyenv unsupported, standalone
  mode less backward-compatible with older macOS versions
- **Very long build times** (minutes to hours for large deps)
- Needs C11 compiler (Clang on macOS — available via Xcode CLI tools)
- AGPL v3 license (with runtime exception) — may be a concern
- Flask compatibility not explicitly documented

**Verdict**: Interesting but risky for our use case. PyInstaller is safer.
Consider only if we need the startup speed improvement.

Sources:
- https://github.com/Nuitka/Nuitka
- https://nuitka.net/
- https://krrt7.dev/en/blog/nuitka-vs-pyinstaller

---

## Option 3: cx_Freeze (Existing Precedent)

**What it does**: Similar to PyInstaller — freezes Python into executables.

**We already use it** in `whisper-local-transcribe/build_setup.py`:
```python
from cx_Freeze import setup, Executable
build_exe_options = {"packages": ['whisper','tkinter','customtkinter']}
executables = [Executable("app.py", icon='images/icon.ico')]
setup(name="Local Transcribe", version="1.2", ...)
```

**Pros**:
- Team familiarity (existing project uses it)
- Decent for simple apps

**Cons**:
- Less popular/maintained than PyInstaller
- Fewer macOS-specific features
- No `--onefile` equivalent (always produces a directory)
- Worse documentation for Flask apps

**Verdict**: We know it, but PyInstaller is better for this project.

---

## Option 4: py-app-standalone (uv-based)

**What it does**: Uses `uv` to create a fully relocatable Python installation
with your app and all deps baked in. No Python or uv needed on target machine.

**Key command**:
```bash
uvx py-app-standalone repo-scanner
```

**How it works**:
1. Downloads standalone Python via `uv python install --managed-python`
2. Installs packages directly into the Python installation (not a venv)
3. Rewrites shebangs and dylib paths to be relative (`@executable_path`)
4. Pre-compiles .pyc files for faster startup

**Pros**:
- Leverages the uv ecosystem (modern, fast)
- Creates a relocatable directory — can be embedded in .app
- No compilation step — faster builds than PyInstaller/Nuitka
- Works cross-platform (but must build on target platform)

**Cons**:
- **Experimental** — primarily tested on macOS, lightly on Linux/Windows
- Doesn't handle non-Python system deps (we need `git`)
- Produces a directory, not a single file
- Less mature than PyInstaller

**Verdict**: Very promising for the future, but too experimental for a release
today. Keep an eye on it. Could replace PyInstaller once mature.

Sources:
- https://github.com/jlevy/py-app-standalone
- https://docs.astral.sh/uv/guides/install-python/

---

## Option 5: uv tool install / pipx

**What it does**: Installs a Python CLI tool into an isolated venv on PATH.

**Key commands**:
```bash
# With uv (auto-downloads Python if needed)
uv tool install repo-scanner

# With pipx
pipx install repo-scanner
```

**Pros**:
- uv auto-downloads Python — user doesn't need it pre-installed
- Clean isolation (own venv per tool)
- Standard PyPI distribution workflow
- Easy updates: `uv tool upgrade repo-scanner`

**Cons**:
- Requires uv or pipx to be installed first
- We'd need a pyproject.toml + PyPI publishing pipeline
- Not truly "zero dependency" — user needs uv at minimum

**Verdict**: Great for Python-aware developers. Should be one of our channels
alongside the binary. Requires pyproject.toml (which we need anyway).

Sources:
- https://docs.astral.sh/uv/guides/install-python/
- https://pydevtools.com/blog/uvx-sh-install-python-tools-without-uv-or-python/

---

## Comparison Matrix

| Approach       | Python needed? | Single file? | Build time | Binary size | Startup | Maturity   |
|----------------|----------------|-------------|------------|-------------|---------|------------|
| PyInstaller    | No (bundled)   | Yes (or dir)| Fast       | ~25-50MB    | 1-3s*   | Excellent  |
| Nuitka         | No (bundled)   | Yes (or dir)| Slow       | ~30-60MB    | Fast    | Good       |
| cx_Freeze      | No (bundled)   | Dir only    | Fast       | ~30-50MB    | Fast    | Fair       |
| py-app-standalone | No (bundled) | Dir only   | Very fast  | ~50-80MB    | Fast    | Experimental|
| uv tool install| No (uv gets it)| N/A        | Fast       | N/A         | Normal  | Good       |
| Docker         | No (in image)  | Image       | Medium     | ~150MB      | Normal  | Excellent  |

*onefile mode — onedir mode has fast startup

---

## Recommendation

**Primary binary approach**: PyInstaller (`--onedir` for .app, `--onefile` for CLI)
**Fallback/future**: py-app-standalone once it matures
**Python devs**: uv tool install / pipx via PyPI
**Servers/Docker users**: Existing Docker workflow
