MODULE_VERSION = "0.0.0"

from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
# 会话 / 会话管理已下沉 core/serial_io/，此处再导出保持既有引用路径可用
from core.serial_io.serial_session import SerialSession
from core.serial_io.serial_session_manager import SerialSessionManager

__all__ = ["SerialComMixin", "SerialSession", "SerialSessionManager"]
