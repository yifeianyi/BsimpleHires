# -*- mode: python ; coding: utf-8 -*-

# FFmpeg ???????????? exe?
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.uic',
    'views.mainwindow',
    'views.workpage',
    'views.progress_dialog',
    'views.settings_dialog',
    'views.version_dialog',
    'services.converter_service',
    'services.ffmpeg_service',
    'services.settings_service',
    'workers.conversion_worker',
    'workers.import_worker',
    'models',
    'ui.UI_main',
    'ui.UI_workPage',
    'ui.UI_ProgressBar',
    'utils.app_info',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/logo.ico', 'assets'),
        ('ffmpeg', 'ffmpeg'),
        ('ui', 'ui'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'tests',
        'distutils',
        'setuptools',
        'pip',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
)
