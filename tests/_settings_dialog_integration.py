# -*- coding: utf-8 -*-
"""N6705CDatalogUI + 设置对话框 集成冒烟测试（临时调试用，offscreen）。

注意：开发环境 DEBUG_MOCK 可能为 False，构造时 auto_connect 设备会发起真实连接
（pending 中卡片视为 busy），断言需排除 busy 卡；结尾 close() 复用 closeEvent 停线程。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication


def main():
    app = QApplication.instance() or QApplication([])

    from ui.pages.n6705c_power_analyzer.datalog import N6705CDatalogUI
    from ui.pages.n6705c_power_analyzer import n6705c_settings_dialog as sm

    ui = N6705CDatalogUI()
    busy_cards = [
        c for c in ui.device_cards
        if ui.is_instrument_busy(c.property("serial"), c.property("visa_resource"))
    ]
    print("datalog ui constructed; cards:", len(ui.device_cards),
          "busy:", len(busy_cards))

    # 增：新设备进列表 → 卡片出现
    devs = sm.load_default_devices()
    devs.append({
        "serial": "MY99999999", "model": "N6705C", "display_ip": "10.0.0.9",
        "visa_resource": "TCPIP0::10.0.0.9::hislip0::INSTR", "auto_connect": False,
    })
    ui.apply_instrument_settings(devs, auto_connect_enabled=False)
    new_card = next((c for c in ui.device_cards
                     if c.property("visa_resource") == "TCPIP0::10.0.0.9::hislip0::INSTR"), None)
    assert new_card is not None, "new card not created"
    # json 中的原有设备卡片也都应存在
    for d in devs:
        assert any(c.property("visa_resource") == d["visa_resource"] for c in ui.device_cards), d
    print("apply add OK; cards:", len(ui.device_cards))

    # 改：serial / auto_connect 更新到卡片
    devs[-1]["serial"] = "MY88888888"
    devs[-1]["auto_connect"] = True
    ui.apply_instrument_settings(devs, auto_connect_enabled=False)
    assert new_card.property("serial") == "MY88888888"
    assert new_card.property("auto_connect") is True
    print("apply edit OK")

    # 删：传空列表 → 非 busy 卡片全部移除，busy（连接中）卡片保留
    ui.apply_instrument_settings([], auto_connect_enabled=False)
    remaining = list(ui.device_cards)
    for c in remaining:
        assert ui.is_instrument_busy(c.property("serial"), c.property("visa_resource")), \
            f"non-busy card not removed: {c.property('serial')}"
    assert all(c in remaining for c in busy_cards), "busy card wrongly removed"
    print("apply remove OK; remaining busy cards:", len(remaining))

    # 恢复现场，避免污染开发配置
    ui.apply_instrument_settings(sm.load_default_devices(), auto_connect_enabled=False)

    # 设置对话框挂在真实页面上构建 + apply
    dialog = sm.N6705CSettingsDialog(ui)
    assert dialog._apply_all()
    dialog.deleteLater()
    print("dialog on real ui OK")

    # 正确清理：close() 复用 closeEvent 停掉连接/扫描线程
    ui.close()
    ui.deleteLater()
    app.processEvents()
    print("ALL OK")


if __name__ == "__main__":
    main()
