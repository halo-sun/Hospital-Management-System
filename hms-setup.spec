# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the HMS Setup Utility (HMS-Setup.exe).

A lightweight, standalone database setup wizard.  Bundles only what
the setup flow needs: tkinter, mysql-connector, and the setup wizard
view — not the full application (matplotlib, reportlab, etc.).

Build from the project root:
    pyinstaller hms-setup.spec
"""

import os
from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath('.')

a = Analysis(
    [os.path.join(ROOT, 'src', 'setup.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'assets', 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'mysql.connector.plugins.caching_sha2_password',
        'bcrypt',
        'src.config',
        'src.config.settings',
        'src.gui.theme',
        'src.gui.setup',
        'src.gui.setup.setup_wizard_view',
        'src.database.connection',
        'src.database.init_db',
    ],
    hookconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed for the setup wizard
        'matplotlib', 'numpy', 'reportlab', 'openpyxl',
        'PIL', 'tkcalendar',
        'pytest', 'black', 'flake8', 'mypy',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HMS-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HMS-Setup',
)
