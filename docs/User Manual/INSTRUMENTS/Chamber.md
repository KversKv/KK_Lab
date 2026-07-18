# Chamber

Chamber 页面用于控制**温箱**（默认 VT6002，可扩展其他支持 Modbus 的型号），实现温度设置、实时温度监控、温度循环序列与温度稳定判定。

## 页面入口

- 导航栏 → `INSTRUMENTS` → `Chamber`
- 对应源码：`ui/pages/chamber/chamber_control_ui.py`（类 `ChamberControlUI`）

## 界面布局

### 1. 顶部连接区
- **Chamber Type**：下拉选择温箱型号（来自 `chamber_module_frame.CHAMBER_TYPES`，当前默认 `vt6002`）。
- **Connection**：根据所选型号自动切换为串口或网口；带搜索按钮和 Connect/Disconnect。
- **连接状态指示**：连接成功后显示绿色 `● Connected`。

### 2. 中央 — Temperature Gauge（温度仪表）
- 圆形仪表盘，显示当前实际温度（ACTUAL TEMP）。
- 支持两种尺寸模式：`large`（默认，280×280）与 `compact`（160×160），自适应窗口宽度。
- 数值字体 `JetBrains Mono` 等宽，单位 `°C`，未读到时显示 `---°C`。

### 3. 设置面板
- **Set Temperature (°C)**：目标温度输入。
- **Chamber ON/OFF**：温箱运行/停止切换。
- **Preset Buttons**：常用温度预设按钮（如 `25°C` / `85°C` / `-40°C`），点击即设。
- 温度循环序列状态指示（运行中 / 已停止 / 步骤索引）。

### 4. 温度循环序列（Loop Sequence）
- 可编辑的温度阶梯序列，每步含目标温度、保持时间。
- `Start Loop` / `Stop Loop` 启停循环。
- 内部由 `QTimer` 1 秒轮询驱动，逐步推进。

### 5. 底部 — Execution Logs
- 通过 `InstrumentStatePoller` 每秒回读温箱实际温度与运行状态。
- 异常（通信失败、超温）会写入日志并显示在状态栏。

## 典型操作流程

### 流程一：恒温保持
1. 选择 Chamber Type（如 `VT6002`）。
2. 点击搜索 → 选择串口或网口资源 → Connect。
3. 状态变绿后，在 Set Temperature 输入 `25` °C。
4. 点击 `Chamber ON` 启动温箱。
5. 仪表盘每秒刷新实际温度，观察趋近目标值。

### 流程二：温度循环
1. 在 Loop Sequence 编辑区添加步骤：如 `[-40°C, 30min] → [25°C, 5min] → [85°C, 30min]`。
2. 点击 `Start Loop`。
3. 页面自动按步骤切换目标温度，每步到达并稳定后才开始倒计时保持时间。
4. 中途可点击 `Stop Loop` 中断。

### 流程三：被自动化测试调用
1. 在 `Consumption Test` / `GPADC Test` / `Charger Status Register Test` 等页面，温箱被作为公共仪器引用。
2. 这些页面通过 `ChamberConnectionMixin` 复用本页连接，无需重复连接。
3. 测试启动时若需要温箱稳定，会调用 `TemperatureStabilizer` 等待温度收敛。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Set Temperature | °C | 目标温度 |
| Actual Temp | °C | 仪表盘实时显示的回读温度 |
| Loop Step | — | 循环序列当前步骤索引 |
| Hold Time | min | 每步到达目标后的保持时间 |

## 注意事项

- **型号扩展**：新增温箱型号需在 `ui/modules/chamber_module_frame.py` 的 `CHAMBER_TYPES` 中登记，并提供对应的 `chamber_baudrate` / `chamber_connection_kind` / `chamber_default_resource` 等元数据。
- **通信方式**：VT6002 默认走串口 Modbus-RTU；网络型号走 Modbus-TCP，资源地址格式不同。
- **稳定判定**：被测试页面调用时使用 `TemperatureStabilizer`，默认判定窗口与容差见 `instruments/chambers/` 实现。
- **安全**：页面只下发温度设置，不直接控制温箱的制冷/加热硬件开关；硬件层由温箱自身的保护逻辑负责。
- **Mock 模式**：`DEBUG_MOCK=True` 时连接 `MockChamber`，可模拟温度变化曲线。
- **不要硬编码端口**：串口号、波特率均来自 `chamber_module_frame` 的元数据与下拉框，禁止写入代码。
