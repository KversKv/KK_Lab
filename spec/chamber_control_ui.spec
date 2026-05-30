# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Chamber Control Standalone Window
#
# ------------------------------------------------------------------
# Build modes (onedir default / onefile optional)
# ------------------------------------------------------------------
#
# Mode 1  onedir (default, recommended for distribution):
#   python -m PyInstaller spec/chamber_control_ui.spec --clean --noconfirm
#   Output: dist/Chamber_Control/
#
# Mode 2  onefile (single EXE, convenient for quick sharing):
#   PowerShell:
#     $env:KK_BUILD_MODE="onefile"; python -m PyInstaller spec/chamber_control_ui.spec --clean --noconfirm
#   CMD:
#     set KK_BUILD_MODE=onefile && python -m PyInstaller spec/chamber_control_ui.spec --clean --noconfirm
#   Output: dist/Chamber_Control.exe
#
# Run with --clean when switching modes to avoid stale build artifacts.

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


def _filter_chamber_binaries(binaries):
    filtered = []
    for item in binaries:
        src, dest = item[0], item[1]
        normalized_src = _normalize_toc_item_path(src)
        normalized_dest = _normalize_toc_item_path(dest)
        if 'pyside6' + os.path.sep in normalized_src or 'pyside6' + os.path.sep in normalized_dest:
            if _is_allowed_qt_binary(item):
                filtered.append(item)
            continue
        if 'numpy' + os.path.sep in normalized_src or 'numpy' + os.path.sep in normalized_dest:
            continue
        if 'numpy.libs' + os.path.sep in normalized_src or 'numpy.libs' + os.path.sep in normalized_dest:
            continue
        if 'pyqtgraph' + os.path.sep in normalized_src or 'pyqtgraph' + os.path.sep in normalized_dest:
            continue
        if os.path.basename(normalized_src) in {'libcrypto-3.dll', 'libssl-3.dll'}:
            continue
        filtered.append(item)
    return filtered


def _filter_chamber_datas(datas):
    filtered = []
    for item in datas:
        src, dest = item[0], item[1]
        normalized_src = _normalize_toc_item_path(src)
        normalized_dest = _normalize_toc_item_path(dest)
        if 'pyside6' + os.path.sep + 'translations' + os.path.sep in normalized_src:
            continue
        if 'pyside6' + os.path.sep + 'translations' + os.path.sep in normalized_dest:
            continue
        if 'pyqtgraph' + os.path.sep in normalized_src or 'pyqtgraph' + os.path.sep in normalized_dest:
            continue
        if 'numpy' + os.path.sep in normalized_src or 'numpy' + os.path.sep in normalized_dest:
            continue
        filtered.append(item)
    return filtered


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

BUILD_MODE = os.environ.get('KK_BUILD_MODE', 'onedir').strip().lower()
if BUILD_MODE not in ('onedir', 'onefile'):
    raise SystemExit(
        f"[spec] Invalid KK_BUILD_MODE={BUILD_MODE!r}, expected 'onedir' or 'onefile'"
    )
print(f"[spec] Chamber_Control build mode = {BUILD_MODE}")

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'ui', 'pages', 'chamber', 'chamber_control_ui.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
        (
            os.path.join(PROJECT_ROOT, 'resources', 'modules', 'SVG_Common'),
            os.path.join('resources', 'modules', 'SVG_Common'),
        ),
        (
            os.path.join(PROJECT_ROOT, 'resources', 'pages', 'chamber_SVGs'),
            os.path.join('resources', 'pages', 'chamber_SVGs'),
        ),
    ],
    hiddenimports=[
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'pyvisa',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        'PySide6.QtWidgets',
        'ui',
        'ui.resource_path',
        'ui.widgets',
        'ui.widgets.button',
        'ui.widgets.dark_combobox',
        'ui.modules',
        'ui.modules.chamber_module_frame',
        'ui.pages',
        'ui.pages.chamber',
        'ui.pages.chamber.chamber_control_ui',
        'core',
        'core.instruments',
        'core.instruments.instrument_session',
        'instruments',
        'instruments.base',
        'instruments.base.instrument_base',
        'instruments.base.visa_instrument',
        'instruments.base.exceptions',
        'instruments.chambers',
        'instruments.chambers.base',
        'instruments.chambers.mt3065',
        'instruments.chambers.vt6002_chamber',
        'instruments.chambers.wt2040_chamber',
        'instruments.mock',
        'instruments.mock.mock_instruments',
        'instruments.factory',
        'log_config',
        'debug_config',
    ],
    hookspath=[os.path.join(PROJECT_ROOT, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pyqtgraph',
        'pyqtgraph.opengl',
        'numpy',
        'numpy.array_api',
        'OpenGL',
        'openpyxl',
        'importlib_resources',
        'serial.tools.list_ports_osx',
        'tkinter', '_tkinter', 'Tkinter', 'turtle', 'turtledemo',
        'setuptools', 'pip', 'wheel',
        'lib2to3', 'idlelib',
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
        'matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter',
        'PyQt5', 'PyQt6', 'PySide2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = _filter_chamber_binaries(a.binaries)
a.datas = _filter_chamber_datas(a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_EXE_COMMON_KWARGS = dict(
    name='Chamber_Control',
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
    icon=os.path.join(PROJECT_ROOT, 'resources', 'icons', 'vt6002.ico'),
)

if BUILD_MODE == 'onedir':
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
        name='Chamber_Control',
    )

else:
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
