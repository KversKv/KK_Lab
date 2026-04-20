# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for N6705C Datalog UI

#run cmd
#python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm


import os

block_cipher = None

# Project root (spec file is in spec/ subdirectory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'pages', 'n6705c_power_analyzer', 'n6705c_datalog_ui.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Include SVG icons
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
    ],
    hiddenimports=[
        'pyvisa',
        'pyvisa_py',
        'pyvisa_py.tcpip',
        'pyvisa_py.protocols',
        'pyvisa_py.protocols.vxi11',
        'pyvisa_py.protocols.rpc',
        'pyqtgraph',
        'PySide6',
        'PySide6.QtSvg',
        'instruments',
        'instruments.power',
        'instruments.power.keysight',
        'instruments.power.keysight.n6705c',
        'instruments.power.keysight.n6705c_datalog_process',
        'instruments.mock',
        'instruments.mock.mock_instruments',
        'ui',
        'ui.widgets',
        'ui.widgets.button',
        'ui.widgets.dark_combobox',
        'ui.styles',
        'ui.modules',
        'log_config',
        'debug_config',
        'openpyxl',
    ],
    hookspath=[os.path.join(PROJECT_ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pyqtgraph.opengl',
        'OpenGL',
        'importlib_resources',
        'serial.tools.list_ports_osx',
        'numpy.array_api',
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
    name='N6705C_Datalog',
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
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'n6705c.ico'),
)