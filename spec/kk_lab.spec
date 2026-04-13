# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for KK_Lab Main Application

#run cmd
#python -m PyInstaller spec/kk_lab.spec --clean --noconfirm


import os

block_cipher = None

# Project root (spec file is in spec/ subdirectory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, 'lib', 'i2c'),
    ],
    binaries=[],
    datas=[
        # Include SVG icons
        (os.path.join(PROJECT_ROOT, 'resources', 'icons'), os.path.join('resources', 'icons')),
        # Include lib/i2c directory (Python modules, DLLs, config, efuse scripts)
        (os.path.join(PROJECT_ROOT, 'lib', 'i2c'), os.path.join('lib', 'i2c')),
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
        'instruments.base',
        'instruments.base.instrument_base',
        'instruments.base.visa_instrument',
        'instruments.base.exceptions',
        'instruments.scopes',
        'instruments.scopes.base',
        'instruments.scopes.keysight',
        'instruments.scopes.keysight.dsox4034a',
        'instruments.scopes.keysight.dsox_lib',
        'instruments.scopes.tektronix',
        'instruments.scopes.tektronix.mso64b',
        'instruments.power',
        'instruments.power.keysight',
        'instruments.power.keysight.n6705c',
        'instruments.chambers',
        'instruments.chambers.vt6002_chamber',
        'instruments.adapters',
        'instruments.factory',
        'core',
        'core.test_manager',
        'core.data_collector',
        'core.controllers',
        'core.controllers.oscilloscope_controller',
        'ui',
        'ui.main_window',
        'ui.widgets',
        'ui.widgets.plot_widget',
        'ui.widgets.sidebar_nav_button',
        'ui.widgets.dark_combobox',
        'ui.pages',
        'ui.pages.power',
        'ui.pages.power.n6705c_top',
        'ui.pages.power.n6705c_ui',
        'ui.pages.power.n6705c_double_ui',
        'ui.pages.power.n6705c_datalog_ui',
        'ui.pages.oscilloscope',
        'ui.pages.oscilloscope.oscilloscope_base_ui',
        'ui.pages.oscilloscope.mso64b_ui',
        'ui.pages.oscilloscope.dsox4034a_ui',
        'ui.pages.pmu',
        'ui.pages.pmu.pmu_test_ui',
        'ui.pages.pmu.pmu_dcdc_efficiency',
        'ui.pages.pmu.pmu_output_voltage',
        'ui.pages.pmu.pmu_isGain_ui',
        'ui.pages.pmu.pmu_oscp_ui',
        'ui.pages.chamber',
        'ui.pages.chamber.vt6002_chamber_ui',
        'ui.pages.test',
        'ui.pages.test.consumption_test',
        'ui.pages.test.gpadc_test_ui',
        'ui.pages.test.clk_test_ui',
        'openpyxl',
        'Bes_I2CIO_Interface',
        'i2c_interface_x64',
        'efuse_script_caller',
        'lib.i2c.Bes_I2CIO_Interface',
        'lib.i2c.i2c_interface_x64',
        'lib.i2c.efuse_script_caller',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='KK_Lab',
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