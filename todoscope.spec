# -*- mode: python ; coding: utf-8 -*-
"""
TodoScope PyInstaller spec — two build targets.

Usage:
  pipenv run pyinstaller todoscope.spec          # builds BOTH targets
  pipenv run pyinstaller todoscope.spec --target cli   # (custom, see below)

Target 1 — "todoscope"   CLI onefile binary   (direct-download distribution)
Target 2 — "TodoScope"   macOS .app bundle     (DMG distribution)
"""

import sys
from pathlib import Path

block_cipher = None

# ── Shared configuration ──────────────────────────────────────────────

_datas = [
    ('scanner/templates', 'scanner/templates'),
    ('scanner/static',    'scanner/static'),
]

_hiddenimports = ['yaml']

_entry = 'scanner/cli.py'

# ── Target 1: CLI onefile binary ──────────────────────────────────────

cli_a = Analysis(
    [_entry],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

cli_pyz = PYZ(cli_a.pure, cipher=block_cipher)

cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    cli_a.binaries,
    cli_a.datas,
    [],
    name='todoscope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ── Target 2: macOS .app windowed bundle ──────────────────────────────

app_a = Analysis(
    [_entry],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

app_pyz = PYZ(app_a.pure, cipher=block_cipher)

app_exe = EXE(
    app_pyz,
    app_a.scripts,
    [],
    exclude_binaries=True,
    name='TodoScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # --windowed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app_coll = COLLECT(
    app_exe,
    app_a.binaries,
    app_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TodoScope',
)

app_bundle = BUNDLE(
    app_coll,
    name='TodoScope.app',
    icon='assets/todoscope.icns',
    bundle_identifier='com.sage-is.todoscope',
)
