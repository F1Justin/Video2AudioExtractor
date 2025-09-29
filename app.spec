# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = []
datas += collect_data_files('ttkbootstrap')
datas += collect_data_files('tkinterdnd2')

# 包含本地 ffmpeg 可执行文件到运行目录的 ffmpeg/ 子目录
datas += [
    ('ffmpeg/ffmpeg.exe', 'ffmpeg'),
    ('ffmpeg/ffprobe.exe', 'ffmpeg'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Video2AudioExtractor',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Video2AudioExtractor'
)

app = BUNDLE(
    coll,
    name='Video2AudioExtractor',
    icon=None,
)


