# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Wriggle Survey
Build command:  pyinstaller WriggleSurvey.spec
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all, copy_metadata

block_cipher = None

# Collect all package data
datas = []
# copy_metadata fixes "No package metadata was found for X" errors
datas += copy_metadata("streamlit")
datas += copy_metadata("pandas")
datas += copy_metadata("numpy")
datas += copy_metadata("plotly")
datas += copy_metadata("matplotlib")
datas += copy_metadata("openpyxl")

datas += collect_data_files("streamlit",  include_py_files=True)
datas += collect_data_files("plotly")
datas += collect_data_files("matplotlib")
datas += collect_data_files("pandas")
datas += collect_data_files("openpyxl")
datas += collect_data_files("altair")

# App source files
datas += [
    ("streamlit_app.py",    "."),
    ("backend",             "backend"),
    ("license_manager.py",  "."),
    ("license_dialog.py",   "."),
]

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pandas",
    "numpy",
    "openpyxl",
    "plotly",
    "plotly.graph_objects",
    "plotly.subplots",
    "matplotlib",
    "matplotlib.pyplot",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_agg",
    "xml.etree.ElementTree",
    "tkinter",
    "tkinter.messagebox",
]

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WriggleSurvey",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # False = pencere açılmaz (sadece browser)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WriggleSurvey",
)
