import os

block_cipher = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

ENTRY_SCRIPT = os.path.abspath(ENTRY_SCRIPT)
APP_NAME = APP_NAME
ICON_PATH = os.path.abspath(ICON_PATH)

BUILD_MODE = os.environ.get('KK_BUILD_MODE', 'onedir').strip().lower()
if BUILD_MODE not in ('onedir', 'onefile'):
    raise SystemExit(
        f"[spec] Invalid KK_BUILD_MODE={BUILD_MODE!r}, expected 'onedir' or 'onefile'"
    )
print(f"[spec] {APP_NAME} build mode = {BUILD_MODE}")

_BASE_HIDDENIMPORTS = [
    'pyvisa',
    'pyvisa_py',
    'pyvisa_py.tcpip',
    'pyvisa_py.protocols',
    'pyvisa_py.protocols.vxi11',
    'pyvisa_py.protocols.rpc',
    'pyqtgraph',
    'numpy',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'openpyxl',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtSvg',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    'log_config',
    'debug_config',
    'ui',
    'ui.resource_path',
    'ui.standalone',
    'ui.theme',
    'ui.widgets',
    'ui.widgets.button',
    'ui.widgets.dark_combobox',
    'ui.widgets.plot_widget',
    'ui.widgets.progress_button',
    'ui.widgets.scrollbar',
    'ui.widgets.start_sequence',
    'ui.utils',
    'ui.utils.icon_utils',
    'ui.styles',
    'ui.modules',
    'ui.modules.execution_logs_module_frame',
    'ui.modules.n6705c_module_frame',
    'ui.modules.oscilloscope_module_frame',
    'ui.modules.chamber_module_frame',
    'ui.modules.keysight_53230a_module_frame',
    'ui.modules.serialCom_module.serialCom_module_frame',
    'ui.modules.serialCom_module.serial_session',
    'ui.modules.serialCom_module.serial_session_manager',
    'core',
    'core.test_manager',
    'core.data_collector',
    'core.auto_baud_detector',
    'core.instruments',
    'core.instruments.instrument_session',
    'core.instruments.instrument_manager',
    'core.instruments.profiles',
    'core.instruments.registry',
    'core.instruments.workers',
    'core.controllers',
    'instruments',
    'instruments.base',
    'instruments.base.instrument_base',
    'instruments.base.visa_instrument',
    'instruments.base.exceptions',
    'instruments.factory',
    'instruments.mock',
    'instruments.mock.mock_instruments',
    'instruments.power',
    'instruments.power.keysight',
    'instruments.power.keysight.n6705c',
    'instruments.power.keysight.n6705c_datalog_process',
    'instruments.scopes',
    'instruments.scopes.base',
    'instruments.scopes.keysight',
    'instruments.scopes.keysight.dsox4034a',
    'instruments.scopes.keysight.dsox_lib',
    'instruments.scopes.tektronix',
    'instruments.scopes.tektronix.mso64b',
    'instruments.chambers',
    'instruments.chambers.base',
    'instruments.chambers.mt3065',
    'instruments.chambers.vt6002_chamber',
    'instruments.chambers.temperature_stabilizer',
    'instruments.frequencyCounter',
    'instruments.frequencyCounter.keysight_53230A',
    'chips',
    'chips.bes_chip_configs',
    'chips.bes_chip_configs.bes_chip_configs',
    'chips.bes_chip_configs.main_chips',
    'chips.bes_chip_configs.pmu_chips',
    'lib.download_tools.download_script',
    'Bes_I2CIO_Interface',
    'i2c_interface_x64',
    'i2c_demo_x64',
    'efuse_script_caller',
    'lib.i2c.Bes_I2CIO_Interface',
    'lib.i2c.i2c_interface_x64',
    'lib.i2c.i2c_demo_x64',
    'lib.i2c.efuse_script_caller',
]

hiddenimports = sorted(set(_BASE_HIDDENIMPORTS + globals().get('EXTRA_HIDDENIMPORTS', [])))

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, 'lib', 'i2c'),
        os.path.join(PROJECT_ROOT, 'lib', 'download_tools'),
        os.path.join(PROJECT_ROOT, 'chips'),
    ],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
        (os.path.join(PROJECT_ROOT, 'resources', 'pages'), os.path.join('resources', 'pages')),
        (os.path.join(PROJECT_ROOT, 'resources', 'modules'), os.path.join('resources', 'modules')),
        (os.path.join(PROJECT_ROOT, 'lib', 'i2c'), os.path.join('lib', 'i2c')),
        (os.path.join(PROJECT_ROOT, 'lib', 'download_tools'), os.path.join('lib', 'download_tools')),
        (os.path.join(PROJECT_ROOT, 'chips'), 'chips'),
        (os.path.join(PROJECT_ROOT, 'helps'), 'helps'),
    ],
    hiddenimports=hiddenimports,
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

_EXE_COMMON_KWARGS = dict(
    name=APP_NAME,
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
    icon=ICON_PATH,
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
        name=APP_NAME,
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
