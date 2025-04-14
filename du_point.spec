# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = []
binaries += collect_dynamic_libs('xml.parsers')


a = Analysis(
    ['du_point.py'],
    pathex=[],
    binaries=binaries,
    datas=[('D:\\PythonProject\\smart_finance\\python_project_1\\.venv\\Lib\\site-packages\\pyecharts\\datasets', '.\\pyecharts\\datasets'), ('D:\\PythonProject\\smart_finance\\python_project_1\\.venv\\Lib\\site-packages\\zhconv\\zhcdict.json', 'zhconv'), ('D:\\PythonProject\\smart_finance\\python_project_1\\.venv\\Lib\\site-packages\\pyecharts\\render\\templates', '.\\pyecharts\\render\\templates')],
    hiddenimports=['xml.parsers.expat'],
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
    name='du_point',
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
