# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\SHARE\\tools\\自制py小工具\\CVEhunter-c\\run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('prompts', 'prompts'), ('assets', 'assets'), ('data', 'data')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='CVEhunter',
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
    icon=['D:\\SHARE\\tools\\自制py小工具\\CVEhunter-c\\assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CVEhunter',
)
