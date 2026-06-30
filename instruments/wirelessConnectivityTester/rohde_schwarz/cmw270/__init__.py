"""CMW270 无线综测仪驱动 (罗德与施瓦茨)。

将 BT / BLE / LTE / WIFI 各制式 Mixin 组合进统一的 CMW270 类。

测试用例入口见同目录 __main__.py, 运行方式::

    python -m instruments.wirelessConnectivityTester.rohde_schwarz.cmw270
"""

from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270.base import CMW270Base
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270.bt import BluetoothMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270.ble import BluetoothLEMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270.lte import LTEMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw270.wifi import WifiMixin


class CMW270(BluetoothMixin, BluetoothLEMixin, LTEMixin, WifiMixin, CMW270Base):
    """R&S CMW270 无线连接综测仪完整驱动。

    用法::

        cmw = CMW270("TCPIP0::10.31.31.236::hislip0::INSTR")
        print(cmw.identify())
        cmw.bt_set_channel(0)
        cmw.bt_init_meval()
        cmw.disconnect()
    """


__all__ = ["CMW270"]
