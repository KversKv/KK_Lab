"""CMW500 通用基类 (继承 R&S CMW 共享 SCPI 基类)。"""

from instruments.wirelessConnectivityTester.rohde_schwarz.base import CMWBase
from log_config import get_logger

logger = get_logger(__name__)


class CMW500Base(CMWBase):
    """CMW500 无线综测仪基类。

    CMW500 为全功能宽带无线综测平台，支持蜂窝 (LTE/5G/WCDMA/GSM) 与非蜂窝
    (BT/BLE/WLAN) 的信令与非信令测试。SCPI 指令集与 CMW270 同源。
    """

    MODEL = "CMW500"
    DEFAULT_RESOURCE = "TCPIP0::10.31.31.236::hislip0::INSTR"
