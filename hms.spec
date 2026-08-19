# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Hospital Management System.

Build from the project root:
    pyinstaller hms.spec

Produces dist/HospitalScheduler.exe (windowed, no console window).

BUNDLING NOTES
--------------
* **tkcalendar** 1.6.1 is pure-Python but its DateEntry widget loads
  Tcl locale data at runtime.  We pull in the full package plus its
  babel dependency (which supplies the locale-data files tkcalendar
  uses for date formatting).

* **Pillow / PIL** must supply ``ImageTk`` for the TkAgg matplotlib
  backend and for any direct image display.  The distro (apt) Pillow
  build omits the ``_tkinter_finder`` bridge; a pip-installed wheel
  includes it.  We explicitly request both ``PIL.ImageTk`` and
  ``PIL._tkinter_finder`` as hidden imports so PyInstaller never
  silently picks up a stub.

* **matplotlib** data files (fonts, style sheets, mpl-data) must be
  bundled in full.  ``collect_all('matplotlib')`` grabs datas, binaries,
  and hidden imports in one pass — far more reliable than hand-curating
  ``mpl-data`` paths.

* **mysql-connector-python** ships a ``caching_sha2_password``
  authentication plugin as a plain ``.py`` file.  The connector
  discovers it via a package-relative import at connect time.  We
  ensure it is collected as a hidden import.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = os.path.abspath('.')

# ── Matplotlib — full data + backend collection ────────────────────────
mpl_datas, mpl_binaries, mpl_hiddenimports = collect_all('matplotlib')

# ── tkcalendar — data files (Tcl locale data) + submodules ────────────
tkc_datas = collect_data_files('tkcalendar')
tkc_hidden = collect_submodules('tkcalendar')

# ── Babel locale-data (tkcalendar dependency) ─────────────────────────
babel_datas = collect_data_files('babel', include_py_files=False)

# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Application assets (icon, etc.)
        (os.path.join(ROOT, 'assets', 'icon.ico'), 'assets'),
        # Matplotlib full data (fonts, stylesheets, mpl-data/)
        *mpl_datas,
        # tkcalendar data files
        *tkc_datas,
        # Babel locale data (needed by tkcalendar for date formatting)
        *babel_datas,
    ],
    hiddenimports=[
        # ── matplotlib backends ─────────────────────────────────
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends._backend_tk',
        # ── Pillow / ImageTk (critical — apt build omits these) ──
        'PIL.ImageTk',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageDraw',
        # ── tkcalendar submodules ────────────────────────────────
        *tkc_hidden,
        # ── mysql-connector auth plugin ──────────────────────────
        'mysql.connector.plugins.caching_sha2_password',
        # ── Other runtime dependencies ───────────────────────────
        'bcrypt',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.pdfgen',
        'openpyxl',
        'dateutil',
        'dateutil.tz',
        'pytz',
        # ── App packages (ensure deep imports are found) ─────────
        'src',
        'src.config',
        'src.config.settings',
        'src.constants',
        'src.constants.enums',
        'src.database',
        'src.database.connection',
        'src.database.init_db',
        'src.services',
        'src.services.auth_service',
        'src.services.document_service',
        'src.services.settings_service',
        'src.repositories',
        'src.auth',
        'src.auth.rbac',
        'src.auth.remember_token',
        'src.controllers',
        'src.gui',
        'src.gui.theme',
        'src.factories',
        'src.models',
        'src.utils',
    ],
    hookconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev-only packages — not needed in shipped exe
        'pytest',
        'pytest_cov',
        'black',
        'flake8',
        'mypy',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
    ],
    noarchive=False,
)

# Remove duplicate entries (PyInstaller may collect the same module twice)
a.datas = list({(dest, src, flag) for dest, src, flag in a.datas})
a.binaries = list({(dest, src, flag) for dest, src, flag in a.binaries})

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HospitalScheduler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed — no console window
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
    name='HospitalScheduler',
)
