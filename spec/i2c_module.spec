# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for I2C Console (独立运行 Demo)
# 入口: ui/modules/IIC_Module/i2c_module_frame.py

#run cmd
#python -m PyInstaller spec/i2c_module.spec --clean --noconfirm


import os

block_cipher = None

# Project root (spec file is in spec/ subdirectory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'modules', 'IIC_Module', 'i2c_module_frame.py')],
    pathex=[
        PROJECT_ROOT,
        # lib/i2c 内 i2c_interface_x64.py 用 sys.path.insert + 平铺 import
        # (from Bes_I2CIO_Interface import ...) 需此目录在 pathex 中
        os.path.join(PROJECT_ROOT, 'lib', 'i2c'),
    ],
    binaries=[],
    datas=[
        # lib/i2c/config/*.dll (BES_USBIO_I2C_X64.dll / CH341DLLA64.dll)
        # 03_GOTCHAS §11: I2C DLL 必须在 spec 中显式收集
        # i2c_interface_x64._resolve_default_dll_path 按 _MEIPASS/lib/i2c/config 查找
        (os.path.join(PROJECT_ROOT, 'lib', 'i2c'), os.path.join('lib', 'i2c')),
        # ui/theme/qss/*.qss — theme.py 用 Path(__file__).parent/"qss" 读取
        # execution_logs_module_frame 顶层 load_qss("log_splitter") / load_qss("log_frame")
        # 必须打包，否则 ImportError: FileNotFoundError on _MEIPASS/ui/theme/qss/xxx.qss
        (os.path.join(PROJECT_ROOT, 'ui', 'theme', 'qss'), os.path.join('ui', 'theme', 'qss')),
        # ExecutionLogsFrame 用的 SVG 图标 (trash/export/filter/logs/chevron-down 等)
        (os.path.join(PROJECT_ROOT, 'resources', 'modules', 'SVG_Logs'),
         os.path.join('resources', 'modules', 'SVG_Logs')),
        # table.qss 通过 $check_svg / $uncheck_svg 引用 checked_*.svg / unchecked_*.svg
        # theme._checkbox_icon_map 按 get_resource_base()/"resources"/"icons" 定位
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtSvg',
        'log_config',
        'debug_config',
        'ui',
        'ui.resource_path',
        'ui.standalone',
        'ui.theme',
        'ui.utils',
        'ui.utils.icon_utils',
        'ui.widgets',
        'ui.widgets.dark_combobox',
        'ui.modules',
        'ui.modules.execution_logs_module_frame',
        'ui.modules.IIC_Module',
        'ui.modules.IIC_Module.i2c_module_frame',
        'ui.modules.IIC_Module.i2c_mixin',
        'ui.modules.IIC_Module.i2c_constants',
        'ui.modules.IIC_Module.i2c_styles',
        'ui.modules.IIC_Module.i2c_widgets',
        'ui.modules.IIC_Module.i2c_workers',
        'ui.modules.IIC_Module.i2c_dsl',
        'ui.modules.IIC_Module.i2c_persistence',
        # lib/i2c: i2c_interface_x64.py 顶部平铺 import Bes_I2CIO_Interface
        'Bes_I2CIO_Interface',
        'i2c_interface_x64',
        'i2c_demo_x64',
        'efuse_script_caller',
        'lib.i2c.Bes_I2CIO_Interface',
        'lib.i2c.i2c_interface_x64',
        'lib.i2c.i2c_demo_x64',
        'lib.i2c.efuse_script_caller',
        # i2c_persistence.py 可选 import yaml
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # I2C 模块不依赖 VISA / 绘图 / Excel / mDNS,排除以缩减体积
        'pyvisa',
        'pyvisa_py',
        'pyvisa_py.tcpip',
        'pyvisa_py.protocols',
        'pyqtgraph',
        'pyqtgraph.opengl',
        'OpenGL',
        'openpyxl',
        'zeroconf',
        'ifaddr',
        'numpy',
        'numpy.array_api',
        'serial',
        'serial.tools',
        'serial.tools.list_ports_osx',
        'instruments',
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
    name='I2C_Console',
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
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'kk_lab.ico'),
)
