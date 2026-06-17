# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SerialCom Module Standalone Window
#
# ------------------------------------------------------------------
# 双模式编译 (onedir 默认 / onefile 可选)
# ------------------------------------------------------------------
#
# 方式 1  onedir  (默认, 推荐用于分发):
#   python -m PyInstaller spec/serialcom_module.spec --clean --noconfirm
#   产物: dist/SerialCom_Module/  (目录, 启动快, 杀软兼容好)
#
# 方式 2  onefile (单文件, 适合临时拷贝/快速分享):
#   PowerShell:
#     $env:KK_BUILD_MODE="onefile"; python -m PyInstaller spec/serialcom_module.spec --clean --noconfirm
#   CMD:
#     set KK_BUILD_MODE=onefile && python -m PyInstaller spec/serialcom_module.spec --clean --noconfirm
#   产物: dist/SerialCom_Module.exe (单 EXE, 启动较慢 3~5s, 杀软误报概率较高)
#
# 切换模式前强烈建议先 --clean, 避免 build/ 残留冲突.
#
# 设计要点:
#   1) onedir 是默认: 启动快, 兼容企业 SRP / AppLocker, 杀软友好
#   2) upx=False    : 避免 Windows Defender / 360 / 火绒因加壳而误报
#   3) onefile 模式会自动设置 runtime_tmpdir=None (释放到 %TEMP%\_MEIxxxx)
#      如果担心 %TEMP% 清理策略, 可手动改成 runtime_tmpdir='.' (EXE 同目录)
#   4) 用户配置/快捷指令一律走 %APPDATA%\KK_Lab\...
#      (见 ui/resource_path.get_user_data_dir), 不写 EXE 同目录或 sys._MEIPASS,
#      两种打包模式下持久化行为完全一致.

import os

block_cipher = None

_ALLOWED_QT_BINARY_NAMES = {
    'd3dcompiler_47.dll',
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',
    'pyside6.abi3.dll',
    'python312.dll',
    'qt6core.dll',
    'qt6gui.dll',
    'qt6network.dll',
    'qt6svg.dll',
    'qt6widgets.dll',
    'qtcore.pyd',
    'qtgui.pyd',
    'qtnetwork.pyd',
    'qtsvg.pyd',
    'qtwidgets.pyd',
    'shiboken6.abi3.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
}

_ALLOWED_QT_PLUGIN_PARTS = (
    os.path.join('PySide6', 'plugins', 'iconengines', 'qsvgicon.dll').lower(),
    os.path.join('PySide6', 'plugins', 'imageformats', 'qico.dll').lower(),
    os.path.join('PySide6', 'plugins', 'imageformats', 'qsvg.dll').lower(),
    os.path.join('PySide6', 'plugins', 'platforms', 'qwindows.dll').lower(),
    os.path.join('PySide6', 'plugins', 'styles', 'qmodernwindowsstyle.dll').lower(),
)


def _normalize_toc_item_path(path):
    return os.path.normpath(path).replace('/', os.path.sep).replace('\\', os.path.sep).lower()


def _is_allowed_qt_binary(item):
    src, dest = item[0], item[1]
    normalized_src = _normalize_toc_item_path(src)
    normalized_dest = _normalize_toc_item_path(dest)
    basename = os.path.basename(normalized_src)
    if basename in _ALLOWED_QT_BINARY_NAMES:
        return True
    return any(part in normalized_src or part in normalized_dest for part in _ALLOWED_QT_PLUGIN_PARTS)


def _filter_serialcom_binaries(binaries):
    filtered = []
    for item in binaries:
        src, dest = item[0], item[1]
        normalized_src = _normalize_toc_item_path(src)
        normalized_dest = _normalize_toc_item_path(dest)
        if 'pyside6' + os.path.sep in normalized_src or 'pyside6' + os.path.sep in normalized_dest:
            if _is_allowed_qt_binary(item):
                filtered.append(item)
            continue
        if os.path.basename(normalized_src) in {'libcrypto-3.dll', 'libssl-3.dll'}:
            continue
        filtered.append(item)
    return filtered


def _filter_serialcom_datas(datas):
    filtered = []
    for item in datas:
        src, dest = item[0], item[1]
        normalized_src = _normalize_toc_item_path(src)
        normalized_dest = _normalize_toc_item_path(dest)
        if 'pyside6' + os.path.sep + 'translations' + os.path.sep in normalized_src:
            continue
        if 'pyside6' + os.path.sep + 'translations' + os.path.sep in normalized_dest:
            continue
        filtered.append(item)
    return filtered


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

# ------------------------------------------------------------------
# 编译模式切换 (通过环境变量 KK_BUILD_MODE)
# ------------------------------------------------------------------
BUILD_MODE = os.environ.get('KK_BUILD_MODE', 'onedir').strip().lower()
if BUILD_MODE not in ('onedir', 'onefile'):
    raise SystemExit(
        f"[spec] Invalid KK_BUILD_MODE={BUILD_MODE!r}, expected 'onedir' or 'onefile'"
    )
print(f"[spec] SerialCom_Module build mode = {BUILD_MODE}")

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'modules', 'serialCom_module', 'serialCom_module_frame.py')],
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
        'numpy',
        'pyqtgraph',
        'ui.modules.serialCom_module.serial_chart_dialog',
        'ui',
        'ui.resource_path',
        'ui.widgets',
        'ui.widgets.dark_combobox',
        'ui.widgets.scrollbar',
        'ui.utils',
        'ui.utils.icon_utils',
        'ui.modules.serialCom_module.serialCom_apple_gpt5p5_style',
        'ui.modules.serialCom_module.serialCom_dark_style',
        'ui.modules.serialCom_module.serial_session',
        'ui.modules.serialCom_module.serial_session_manager',
        'core',
        'core.auto_baud_detector',
        'log_config',
        'debug_config',
    ],
    hookspath=[os.path.join(PROJECT_ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 原有 (注意: pyqtgraph / numpy 是 Chart 功能依赖, 不能排除)
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

a.binaries = _filter_serialcom_binaries(a.binaries)
a.datas = _filter_serialcom_datas(a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_EXE_COMMON_KWARGS = dict(
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

if BUILD_MODE == 'onedir':
    # onedir: EXE 仅含引导 + pyz, 二进制/资源由 COLLECT 放到目录下
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **_EXE_COMMON_KWARGS,
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

else:  # onefile
    # onefile: 所有内容打进单 EXE; 启动时自解压到 runtime_tmpdir
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        exclude_binaries=False,
        runtime_tmpdir=None,
        **_EXE_COMMON_KWARGS,
    )
