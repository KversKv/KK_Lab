# GPADC Test

GPADC（General Purpose ADC）测试：验证芯片内部通用 ADC 的采样精度，支持 1000 次连续采样统计、Force Voltage 通道扫描、高低温测试、温度一致性测试 4 个测试项。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `GPADC Test`
- 对应源码：`ui/pages/pmu_test/gpadc_test_ui.py`（`GPADCTestUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，提供 Force Voltage。
- **Chamber 连接卡片**：`ChamberConnectionMixin`（高低温项需要）。
- **Serial 连接卡片**：`SerialComMixin` MODE_FULL，向 DUT 发送采样命令。
- **Test Config 卡片**：
  - Test Item 下拉：`1000CNT TEST` / `Force Voltage Test` / `High-Low Temp Test` / `Temp Consistency Test`
  - 不同测试项显示不同子配置（采样次数、电压范围、温度点列表等）

### 2. 右侧结果区
- **校准曲线**（Force Voltage Test）：ADC Code vs Input Voltage，含 `compute_calibration` 拟合线。
- **统计直方图**（1000CNT）：均值、方差、最大最小值。
- **温度曲线**（High-Low Temp / Temp Consistency）：ADC Code vs Temperature。

### 3. 底部 — Execution Logs
- 打印每次采样的原始码、换算电压、统计结果。
- 温度测试项含 `TemperatureStabilizer` 等待稳定的日志。

## 典型操作流程

### 1000CNT TEST（采样稳定性）
1. 连接 N6705C + USB-I2C + 串口。
2. Test Item 选 `1000CNT TEST`。
3. 设目标通道与采样次数 1000。
4. `▷ Start` → DUT 连续采样 1000 次 → 统计均值/方差/极值 → 输出直方图。

### Force Voltage Test（线性度）
1. Test Item 选 `Force Voltage Test`。
2. 设电压扫描范围（如 0~1.8V，步进 100mV）。
3. 每个电压点 N6705C 输出 → DUT 采样 → 记录 ADC Code。
4. 测试完成 `compute_calibration` 拟合 INL/DNL。

### High-Low Temp Test（温度特性）
1. 先在 Chamber 页连接温箱。
2. Test Item 选 `High-Low Temp Test`。
3. 设温度点列表（如 -40 / 25 / 85 °C）。
4. `▷ Start` → 每个温度点等待稳定 → 在该温度下采样 → 输出温度曲线。

### Temp Consistency Test（温度一致性）
1. 类似 High-Low Temp，但比较多个通道在同一温度下的偏差。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Sample Count | — | 1000CNT 测试的采样次数（默认 1000） |
| Voltage Range | V | Force Voltage 扫描范围 |
| Temperature Points | °C | 高低温测试的温度点列表 |
| ADC Code | — | DUT 回读的原始 ADC 码值 |

## 注意事项

- **仪器依赖映射**：`INSTRUMENT_MAP` 字典声明每个测试项需要的仪器，启动前会校验连接完整性。
- **温度稳定判定**：使用 `TemperatureStabilizer`，等待窗口与容差见 `instruments/chambers/`。
- **串口作用**：向 DUT 固件发送采样命令，波特率默认 921600。
- **AI 契约**：实现 5 个能力。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C / 温箱 / I2C 全部走 Mock。
- **AI 回填高亮**：被 AI 修改的输入框会高亮绿色边框 1.5 秒。
