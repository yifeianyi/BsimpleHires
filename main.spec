# -*- mode: python ; coding: utf-8 -*-

import sys
import glob
from PyInstaller.utils.hooks import collect_data_files

# ========= ffmpeg外部化 =========
# 不再打包ffmpeg文件，改为外部依赖
# ffmpeg_files = [(f, "ffmpeg") for f in glob.glob("ffmpeg/*")]

# ========= 必须的 hidden imports =========
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.uic',
    'views.mainwindow',
    'views.workpage',
    'views.progress_dialog',
    'services.converter_service',
    'services.ffmpeg_service',
    'workers.conversion_worker',
    'models',
    'ui.UI_main',
    'ui.UI_workPage',
    'ui.UI_ProgressBar'
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/logo.ico', 'assets'),
        ('ui', 'ui'),  # 添加UI文件
        # ffmpeg文件外部化，不打包进exe
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'distutils',
        'setuptools',
        'pip',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas'
    ],
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
    name='BsimpleHires',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用UPX压缩，加快启动速度
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico'
)