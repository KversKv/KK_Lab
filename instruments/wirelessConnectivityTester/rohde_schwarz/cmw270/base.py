"""CMW270 通用基类 (继承 R&S CMW 共享 SCPI 基类)。"""

from instruments.wirelessConnectivityTester.rohde_schwarz.base import CMWBase
from log_config import get_logger

logger = get_logger(__name__)


class CMW270Base(CMWBase):
    """CMW270 无线综测仪基类。

    CMW270 主打非信令 (RF 测量) 应用，覆盖 BT / BLE / WLAN / 蜂窝等制式的
    生产与研发测试。SCPI 指令集与 CMW500 同源。
    """

    MODEL = "CMW270"
    DEFAULT_RESOURCE = "TCPIP0::10.31.31.236::hislip0::INSTR"
