"""兼容旧导入路径：执行器已迁移到 core.orchestrator。"""

from core.orchestrator.executor import *  # noqa: F401,F403
from core.orchestrator.runtime import execute_children as _execute_children
from core.orchestrator.runtime import execute_node as _execute_node
