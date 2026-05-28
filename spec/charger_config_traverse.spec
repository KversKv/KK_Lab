# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))
ENTRY_SCRIPT = os.path.join(PROJECT_ROOT, 'ui', 'pages', 'charger_test', 'config_traverse_test.py')
APP_NAME = 'Charger_Config_Traverse'
ICON_PATH = os.path.join(PROJECT_ROOT, 'resources', 'icons', 'charger_test.ico')

_COMMON_SPEC = os.path.join(PROJECT_ROOT, 'spec', '_standalone_ui_common.py')
exec(compile(open(_COMMON_SPEC, encoding='utf-8').read(), _COMMON_SPEC, 'exec'))
