# VminHunter

VminHunter 用于探测芯片能稳定工作的**最低电压边界（Vmin）**：在多个电压点逐步降压，监测 DUT 是否死机/异常，找到稳定运行的最低电压。

## 页面入口

- 导航栏 → `AUTOMATION` → `VminHunter`
- 对应源码：`ui/pages/vmin_hunter/vmin_hunter_ui.py`（`VminHunterUI`）
- 详细架构见 `docs/ai/VminHunter/ViminHunterStructure.md`

## 界面布局

布局参考 Consumption Test：左侧配置列 + 右侧监控区 + 底部 UART 日志。

### 1. 左侧配置区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，提供外部供电（External Supply 模式）。
- **Chamber 连接卡片**：`ChamberConnectionMixin`，温度扫描时用。
- **MCU Pwr/Reset Config 卡片**：`McuPwrResetConfigMixin`，控制 DUT 上电/复位。
- **Serial 连接卡片**：`SerialComMixin` MODE_FULL，波特率默认 921600，监听 DUT UART 日志判定死机。
- **Test Config 卡片**：
  - **Test Mode**：
    - `Internal Voltage (IIC)`：通过 I2C 写 PMU 内部电压寄存器
    - `External Supply (N6705C)`：通过 N6705C 外部供电扫描
  - Voltage Sweep Range / Step：电压扫描范围与步进
  - Current Limit (mA)：电流限值，默认 20mA（范围 0.1~5000mA）
  - VCOREL Enabled：是否启用 VCOREL 监测
  - Temp Enabled：是否启用温度扫描
- **Channel Config 卡片**：选择 N6705C 通道映射。

### 2. 右侧监控区
- **电压点遍历结果表**：每个电压点一行，列含电压、状态（PASS/FAIL/未测）、运行时长、备注。
- **死机记录区**：记录每次死机时的电压点、UART 日志快照、异常类型。

### 3. 底部 — Execution Logs
- UART 日志实时滚动，死机检测算法输出（如长时间无心跳、字符乱码等）。
- 异常带 `exc_info=True` 详细堆栈。

## 典型操作流程

1. 连接 N6705C（外部供电模式）或 USB-I2C（内部电压模式）+ MCU IO（控制 DUT 复位）+ 串口（监听 UART）。
2. 进入本页 → 选择 Test Mode（如 `External Supply (N6705C)`）。
3. 设电压扫描范围 1.0V~0.6V，步进 20mV。
4. 设 Current Limit 20mA。
5. 选择 N6705C 通道映射（Vin 接 DUT 主电源）。
6. 点击 `▷ Start`。
7. `SleepVminRunner` 启动：对每个电压点：
   - 设置目标电压
   - 复位 DUT → 等待启动
   - 监测 UART 心跳 / I2C 状态
   - 检测死机 → 记录 FAIL；正常运行 N 秒 → 记录 PASS
8. 测试完成输出 Vmin 边界报告。

## 关键参数说明

| 参数 | 单位 | 默认 | 说明 |
|---|---|---|---|
| Test Mode | — | — | IIC 内部电压 / N6705C 外部供电 |
| Voltage Range | V | — | 扫描电压范围 |
| Step | mV | — | 扫描步进 |
| Current Limit | mA | 20 | 电流限值（OCP） |
| Settling Time | s | — | 电压设置后等待稳定时间 |
| Heartbeat Timeout | s | — | UART 心跳超时判定死机 |

## 注意事项

- **死机判定与恢复**：核心逻辑在 `core/vmin_hunter/`，包含 UART 心跳监测、I2C 状态查询、自动复位重试；UI 层只负责配置与展示，不阻塞 IO。
- **测试模式差异**：
  - Internal Voltage 模式走 I2C 写 PMU 寄存器，扫描范围受芯片 PMU 电压档位限制。
  - External Supply 模式走 N6705C 直接供电，扫描范围更宽，但需要硬件改线。
- **VCOREL 监测**：勾选后会同步读 VCOREL 状态位，作为辅助判据。
- **温度扫描**：勾选 Temp Enabled 后会嵌套温度循环，每个温度点单独扫电压。
- **I2CWidthFlag**：内部电压模式涉及 I2C 寄存器宽度，由 `Bes_I2CIO_Interface` 配置。
- **AI 集成**：本页面未单独注册 `ai_capabilities`（Vmin 探底流程较复杂，建议人工监控）。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C / 温箱 / MCU IO 走 Mock，UART 日志为模拟。
- **结果文件**：输出到 `Results/vmin_hunter/<时间戳>/`，含电压点表 CSV + 死机日志快照 + Vmin 报告。
