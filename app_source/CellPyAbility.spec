# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


APP_DIR = Path(SPECPATH).resolve()
REPO_ROOT = APP_DIR.parent
SRC_DIR = REPO_ROOT / 'src'


a = Analysis(
    [str(APP_DIR / 'CellPyAbilityGUI.py')],
    pathex=[str(APP_DIR), str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(APP_DIR / 'CellPyAbilityLogo.png'), '.'),
        (str(APP_DIR / 'Potential_New_Logo.png'), '.'),
        (str(APP_DIR / 'CellPyAbilityIcon.ico'), '.'),
        (str(APP_DIR / 'CellPyAbility.cppipe'), '.'),
    ],
    hiddenimports=[
        'cellpyability',
        'cellpyability.toolbox',
        'cellpyability.cli',
        'cellpyability.gda_analysis',
        'cellpyability.synergy_analysis',
        'cellpyability.simple_analysis',
        'cellpyability.batch_analysis',
        'cellpyability.GDA_interactive_map',
        'cellpyability.synergy_interactive_map',
        'matplotlib.backends.backend_macosx',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['IPython', 'jupyter', 'notebook', 'nbconvert', 'nbformat', 'qtconsole'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CellPyAbility',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_DIR / 'CellPyAbilityIcon.ico')
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CellPyAbility',
)
