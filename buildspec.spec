# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for buildspec

a = Analysis(
    ['cli/app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'cli.commands.create_epic',
        'cli.commands.create_tickets',
        'cli.commands.execute_epic',
        'cli.commands.execute_ticket',
        'cli.commands.init',
        'cli.core.claude',
        'cli.core.config',
        'cli.core.context',
        'cli.core.prompts',
        'cli.core.validation',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='buildspec',
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
