# Consumption Test

Consumption Test 是芯片**功耗测试**套件，包含固件下载、芯片识别与功耗测量，支持常温自动测试与高低温功耗扫描两个子页面。

## 子页面索引

| 子页面 | 测试目标 | 主要仪器 |
|---|---|---|
| [Auto Test](./Auto%20Test.md) | 常温自动功耗测试（含固件下载、芯片识别、多种功耗模式切换） | N6705C + MCU IO + 串口 |
| [High-Low Temperature Test](./High-Low%20Temperature%20Test.md) | 高低温功耗扫描 | N6705C + 温箱 + MCU IO |

## 页面入口

- 导航栏 → `AUTOMATION` → `Consumption Test` → 悬停展开子菜单。
- 对应源码：`ui/pages/consumption_test/consumption_test_wrapper.py`（`ConsumptionTestWrapper`，隐藏顶部 Tab）。
- 子页面：`consumption_test.py` / `high_low_temp_test_ui.py`。

## 共用约定

- **固件下载**：Auto Test 内置固件下载功能，通过 MCU IO（YD-RP2040 或 CH9114F）将固件烧录到 DUT；下载前自动 `detect_chip_from_bin` 识别芯片型号。
- **芯片配置**：从 `chips/bes_chip_configs/bes_chip_configs.py::SUPPORTED_CHIPS` 读取支持的芯片列表与配置。
- **功耗模式**：支持 Force Normal / Force Sleep / Force High 等多种模式切换，由 `core/consumption_test/workers.py::_ConsumptionTestForceWorker` / `_ConsumptionTestForceHighWorker` 实现。
- **电流单位统一**：所有电流值通过 `_format_current_unified` 统一为 mA 或 μA 显示。
- **仪器连接**：通过 `N6705CConnectionMixin` / `SerialComMixin`（MODE_INLINE）复用会话。
- **AI 契约**：Auto Test 实现 5 个能力；High-Low Temp Test 未单独实现 AI 契约。
- **结果文件**：输出到 `Results/consumption_test/<时间戳>/`，含 CSV + HTML 报告。
