# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SerialCom Module Standalone Window

#run cmd
#python -m PyInstaller spec/serialcom_module.spec --clean --noconfirm


import os

block_cipher = None

# Project root (spec file is in spec/ subdirectory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'modules', 'serialCom_module_frame.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Include SVG icons used by SerialCom module
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
        (os.path.join(PROJECT_ROOT, 'resources', 'modules'), os.path.join('resources', 'modules')),
    ],
    hiddenimports=[
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'PySide6',
        'PySide6.QtSvg',
        'ui',
        'ui.resource_path',
        'ui.widgets',
        'ui.widgets.dark_combobox',
        'ui.widgets.scrollbar',
        'ui.styles',
        'ui.modules',
        'log_config',
        'debug_config',
    ],
    hookspath=[os.path.join(PROJECT_ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pyqtgraph',
        'pyqtgraph.opengl',
        'OpenGL',
        'pyvisa',
        'pyvisa_py',
        'numpy.array_api',
        'openpyxl',
        'importlib_resources',
        'serial.tools.list_ports_osx',
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
    name='SerialCom_Module',
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
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'serialcom_module.ico'),
)
