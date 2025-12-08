# -*- mode: python ; coding: utf-8 -*-

import sys
import glob
from PyInstaller.utils.hooks import collect_data_files

# ========= 收集 PyQt6 必须的 DLL =========
pyqt6_plugins = collect_data_files('PyQt6', includes=['**/plugins/**/*.dll'])
pyqt6_data = collect_data_files('PyQt6', includes=['**/Qt6/**/*.dll'])

# ========= 收集 ffmpeg 目录 =========
# 关键：必须收集目录下每个文件，否则 PyInstaller 不会递归复制
ffmpeg_files = [(f, "ffmpeg") for f in glob.glob("ffmpeg/*")]

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
        ('ui/main.ui', 'ui'),
        ('ui/workPage.ui', 'ui'),
        ('ui/ProgressBar.ui', 'ui'),
        ('test_ffmpeg.py', '.'),  # 添加测试脚本
        *ffmpeg_files  # 添加ffmpeg文件
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加 PyQt6 的数据文件
pyqt6_datas = collect_data_files('PyQt6')
pyqt6_binaries = collect_data_files('PyQt6', includes=['**/*.dll'])

for src, dst in pyqt6_binaries:
    a.binaries.append((src, dst, 'BINARY'))

for src, dst in pyqt6_datas:
    a.datas.append((src, dst, 'DATA'))

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
    upx=True,
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