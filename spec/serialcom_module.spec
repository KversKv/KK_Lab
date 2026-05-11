# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SerialCom Module Standalone Window

#run cmd
#python -m PyInstaller spec/serialcom_module.spec --clean --noconfirm
#
# 输出形式: onedir
#   - 产物目录: dist/SerialCom_Module/
#   - 启动入口: dist/SerialCom_Module/SerialCom_Module.exe
#   - 分发方式: 整个 dist/SerialCom_Module/ 打成 zip 或用 Inno Setup 包成安装器
#
# 设计要点 (面向分发场景):
#   1) onedir 模式: 启动快, 杀软误报率低, 兼容企业 SRP/AppLocker
#   2) upx=False : 避免 Windows Defender / 360 / 火绒因加壳而误报
#   3) 扩展 excludes: 排除 PySide6 中本模块不需要的子模块, 进一步缩小体积
#   4) 用户配置/快捷指令一律走 %APPDATA%\KK_Lab\... (见 ui/resource_path.get_user_data_dir),
#      不写入安装目录, 兼容 C:\Program Files\ 受限权限场景

import os

block_cipher = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'modules', 'serialCom_module_frame.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
        (os.path.join(PROJECT_ROOT, 'resources', 'modules'), os.path.join('resources', 'modules')),
    ],
    hiddenimports=[
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'PySide6',
        'PySide6.QtSvg',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'numpy',
        'pyqtgraph',
        'ui',
        'ui.resource_path',
        'ui.widgets',
        'ui.widgets.plot_widget',
        'ui.widgets.dark_combobox',
        'ui.widgets.sidebar_nav_button',
        'ui.widgets.progress_button',
        'ui.widgets.button',
        'ui.widgets.scrollbar',
        'ui.widgets.start_sequence',
        'ui.styles',
        'ui.modules',
        'log_config',
        'debug_config',
    ],
    hookspath=[os.path.join(PROJECT_ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 原有
        'pyqtgraph.opengl',
        'OpenGL',
        'pyvisa',
        'pyvisa_py',
        'numpy.array_api',
        'openpyxl',
        'importlib_resources',
        'serial.tools.list_ports_osx',
        # 标准库无用项 (注意: pydoc / xmlrpc / http / unittest / distutils 等
        # 经常被 numpy / pyqtgraph / pyvisa-py 在 import 阶段隐式触发, 不能排除)
        'tkinter', '_tkinter', 'Tkinter', 'turtle', 'turtledemo',
        'setuptools', 'pip', 'wheel',
        'lib2to3', 'idlelib',
        # PySide6 未使用的 Qt 模块 (体积大头)
        'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
        'PySide6.QtBluetooth', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtNetworkAuth', 'PySide6.QtNfc', 'PySide6.QtPdf',
        'PySide6.QtPositioning', 'PySide6.QtPrintSupport',
        'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D',
        'PySide6.QtQuickControls2', 'PySide6.QtQuickWidgets',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSensors',
        'PySide6.QtSerialBus', 'PySide6.QtSerialPort',
        'PySide6.QtSpatialAudio', 'PySide6.QtSql', 'PySide6.QtTest',
        'PySide6.QtTextToSpeech', 'PySide6.QtWebChannel',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick',
        'PySide6.QtWebEngineWidgets', 'PySide6.QtWebSockets',
        'PySide6.QtHelp', 'PySide6.QtDesigner', 'PySide6.QtUiTools',
        # numpy 测试 / f2py
        'numpy.tests', 'numpy.f2py', 'numpy.distutils', 'numpy.testing',
        # 其它
        'matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter',
        'PyQt5', 'PyQt6', 'PySide2',
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
    [],
    exclude_binaries=True,
    name='SerialCom_Module',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'serialcom_module.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SerialCom_Module',
)
