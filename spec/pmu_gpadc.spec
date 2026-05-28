# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))
ENTRY_SCRIPT = os.path.join(PROJECT_ROOT, 'ui', 'pages', 'pmu_test', 'gpadc_test_ui.py')
APP_NAME = 'PMU_GPADC'
ICON_PATH = os.path.join(PROJECT_ROOT, 'resources', 'icons', 'pmu_test.ico')

_COMMON_SPEC = os.path.join(PROJECT_ROOT, 'spec', '_standalone_ui_common.py')
exec(compile(open(_COMMON_SPEC, encoding='utf-8').read(), _COMMON_SPEC, 'exec'))
