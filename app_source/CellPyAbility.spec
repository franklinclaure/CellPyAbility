# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['CellPyAbilityGUI.py'],
    pathex=['.', '../../src'],
    binaries=[],
    datas=[
    ('CellPyAbilityLogo.png', '.'),
    ('CellPyAbilityIcon.ico', '.'),
    ('CellPyAbility.cppipe', '.'),
    ],
    hiddenimports=['cellpyability', 'cellpyability.toolbox', 'cellpyability.gda_analysis', 'cellpyability.synergy_analysis', 'cellpyability.simple_analysis'],
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
    icon='CellPyAbilityIcon.ico'
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
