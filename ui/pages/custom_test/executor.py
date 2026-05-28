"""兼容旧导入路径：执行器已迁移到 core.custom_test。"""

from core.custom_test.executor import *  # noqa: F401,F403
from core.custom_test.runtime import execute_children as _execute_children
from core.custom_test.runtime import execute_node as _execute_node
