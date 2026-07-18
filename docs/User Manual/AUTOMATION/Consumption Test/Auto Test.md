# Consumption Test — Auto Test

常温自动功耗测试，集成固件下载、芯片识别、多种功耗模式切换与电流测量。

## 页面入口

- 导航栏 → `AUTOMATION` → `Consumption Test` → 子菜单 `Auto Test`
- 对应源码：`ui/pages/consumption_test/consumption_test.py`（`ConsumptionTestUI`）

## 界面布局

### 1. 顶部 — 固件下载与芯片配置区
- **Firmware Path**：固件 .bin 文件路径选择。
- **MCU IO 连接**：MCU 类型切换（YD-RP2040 / CH9114F）+ 端口选择 + Connect。
- **Chip Selector**：手动选择芯片型号（下载前会自动 `detect_chip_from_bin` 识别）。
- **Download Mode Toggle**：下载模式切换（如 Normal / Forced）。
- **Download Button**（ProgressButton）：点击下载固件，按钮内嵌进度条。

### 2. 左侧 — 仪器连接区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，电流测量通道。
- **Serial 连接卡片**：`SerialComMixin` MODE_INLINE，向 DUT 发送控制命令（如进入 Sleep）。

### 3. 中部 — 控制方法与极性区
- **Control Method Toggle**：控制方式切换（MCU IO / Serial）。
- **Polarity Toggle**：电流测量极性切换（高边 / 低边）。

### 4. 右侧 — 结果区
- **Result Table**：模式 / 设置电流 / 实测电流 / 误差 / PASS-FAIL。
- 多种功耗模式行：Normal / Sleep / Force High 等。

### 5. 底部 — Execution Logs
- 打印下载进度、芯片识别结果、功耗模式切换命令、N6705C 回读。

## 典型操作流程

1. 连接 N6705C（电流通道接 DUT 主电源）+ MCU IO（接 DUT 下载接口）+ 串口（接 DUT UART）。
2. 选择固件 .bin 文件 → 点击 Download → 等待下载完成（按钮进度条到 100%）。
3. 自动识别芯片型号；如识别失败，手动从下拉选择。
4. 选择 Control Method（建议 MCU IO）。
5. 选择要测量的功耗模式（如 Sleep / Normal / Force High）。
6. 点击 `▷ Start` → `_ConsumptionTestForceWorker`（或 ForceHigh 版本）逐项切换模式 → 等待稳定 → N6705C 回读电流。
7. 测试完成保存 CSV + HTML 报告。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Firmware Path | — | 固件 .bin 文件路径 |
| Chip | — | 芯片型号（来自 SUPPORTED_CHIPS） |
| Control Method | — | MCU IO 或 Serial |
| Mode | — | 功耗模式（Normal/Sleep/Force High 等） |
| Measured Current | mA 或 μA | N6705C 实测电流（自动单位） |

## 注意事项

- **MCU IO 类型**：YD-RP2040 走 InstrumentManager 的 `serial_raw_repl`；CH9114F 走本地 worker 连接，不共用 `serial_raw_repl`。
- **芯片识别**：`detect_chip_from_bin` 从 .bin 头部识别型号；识别失败时需手动选择，否则下载可能失败。
- **ProgressButton**：下载按钮内嵌进度条，下载中按钮禁用，完成后恢复。
- **电流单位自动切换**：`CURRENT_UNIT` 与 `_UNIT_CONFIG` 控制何时显示 mA / μA，`_format_current_unified` 统一格式化。
- **AI 契约**：实现 5 个能力。
- **AI 高风险**：`Start` 已注册为高风险动作。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C / I2C / MCU IO 走 Mock。
- **结果文件**：输出到 `Results/consumption_test/<时间戳>/`，含 CSV + HTML（含 PASS/FAIL 表）。
