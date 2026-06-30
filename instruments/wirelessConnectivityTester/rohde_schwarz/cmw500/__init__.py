"""CMW500 无线综测仪驱动 (罗德与施瓦茨)。

将 BT / BLE / LTE / WIFI 各制式 Mixin 组合进统一的 CMW500 类。

测试用例入口见同目录 __main__.py, 运行方式::

    python -m instruments.wirelessConnectivityTester.rohde_schwarz.cmw500
"""

from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500.base import CMW500Base
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500.bt import BluetoothMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500.ble import BluetoothLEMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500.lte import LTEMixin
from instruments.wirelessConnectivityTester.rohde_schwarz.cmw500.wifi import WifiMixin


class CMW500(BluetoothMixin, BluetoothLEMixin, LTEMixin, WifiMixin, CMW500Base):
    """R&S CMW500 无线连接综测仪完整驱动。

    用法::

        cmw = CMW500("TCPIP0::10.31.31.236::hislip0::INSTR")
        print(cmw.identify())
        cmw.lte_set_band("OB1")
        cmw.lte_cell_on()
        cmw.disconnect()
    """


__all__ = ["CMW500"]
