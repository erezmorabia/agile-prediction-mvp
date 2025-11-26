# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get project root directory
project_root = Path(__file__).parent.absolute()

block_cipher = None

# Collect data files to include (only if they exist)
datas = [
    # Include web static files
    (str(project_root / 'web'), 'web'),
]

# Include data files if they exist
data_file1 = project_root / 'data' / 'raw' / 'combined_dataset.xlsx'
if data_file1.exists():
    datas.append((str(data_file1), 'data/raw'))

data_file2 = project_root / 'data' / 'raw' / '20250204_Cleaned_Dataset.xlsx'
if data_file2.exists():
    datas.append((str(data_file2), 'data/raw'))

a = Analysis(
    ['src/web_main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.loops.uvloop',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AgilePredictionSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console to see server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an icon file here if you have one
)

