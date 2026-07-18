# Oscilloscope

Oscilloscope 页面用于控制**示波器**（支持 Tektronix MSO64B 与 Keysight DSOX4034A），进行通道配置、时基/触发设置、波形捕获与测量值轮询。

## 页面入口

- 导航栏 → `INSTRUMENTS` → `Oscilloscope`
- 对应源码：`ui/pages/oscilloscope/oscilloscope_base_ui.py`（基类 `OscilloscopeBaseUI`）
- 子类 `MSO64BTop` / DSOX4034A 专用控制器在 `ui/pages/oscilloscope/mso64b_top.py`

## 界面布局

### 1. 顶部连接区
- VISA Resource 下拉 + 搜索按钮 + Connect/Disconnect。
- 连接状态指示灯。
- 连接成功后自动识别示波器型号，并切换到对应通道配色（Tektronix / Keysight 各自配色）。

### 2. 通道卡片栏（4 通道）
- 每个通道一张卡片，显示通道号、耦合（AC/DC）、刻度（Scale）、偏移（Offset）、当前颜色。
- 选中通道高亮，参数编辑区显示该通道设置。
- 通道卡片右上角有开启/关闭拨动开关。

### 3. 通道参数编辑区
- **Scale**：垂直刻度（V/div）
- **Offset (V)**：垂直偏移
- **Coupling**：AC / DC 切换（`CouplingToggle`）
- **Channel Color**：颜色指示（按型号自动配色）

### 4. 时基与触发区
- **Time Scale**：水平时基（如 `1us`、`10ms`），通过 `TimeScaleEdit` 编辑
- **Trigger Slope**：POS / NEG / EITH（`TriggerModeToggle`）
- **Trigger Level**：触发电平（V）
- **Run / Stop**：`RunStopToggle` 切换示波器运行/停止采集

### 5. 测量值面板
- 支持的测量类型：`PK2PK` / `FREQUENCY` / `MEAN` / `VMAX` / `VMIN` / `RMS`
- 添加测量项后，每 0.5 秒轮询刷新测量值卡片。

### 6. 波形捕获
- `Capture` 按钮（相机图标）触发单次波形捕获，捕获过程中显示 `CaptureLoadingOverlay` 加载遮罩。

## 典型操作流程

### 流程一：连接并设置通道
1. 点击搜索按钮 → 选择目标示波器 VISA 资源 → Connect。
2. 状态灯变绿，通道卡片栏出现 4 个通道。
3. 点击通道 1 卡片 → 设 Scale `0.1` V/div、Offset `0` V、Coupling `DC`。
4. 打开通道 1 开关。
5. 修改任意参数后 Apply 按钮变脏（紫色高亮），点击 Apply 下发。

### 流程二：设置触发并捕获波形
1. 设 Trigger Slope `POS`、Trigger Level `1.25` V。
2. 设 Time Scale `1us`。
3. 点击 `Run` 让示波器连续采集；或保持 `Stop` 后点 `Capture` 做单次捕获。
4. 捕获完成后波形显示在示波器屏幕（仪器本体）上，本页面回读测量值。

### 流程三：添加测量项
1. 在测量面板点击 `Add Measurement`。
2. 选择测量类型（如 `FREQUENCY`）+ 通道。
3. 测量卡片出现并每 0.5 秒刷新当前值。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Scale | V/div | 垂直刻度，决定波形纵向每格电压 |
| Offset | V | 垂直偏移，将波形上下平移 |
| Time Scale | s/div | 水平时基，决定波形横向每格时间 |
| Trigger Level | V | 触发电平 |
| Trigger Slope | — | 触发边沿：上升/下降/两者 |

## 注意事项

- **型号自动识别**：连接后页面会根据回读的 `*IDN?` 自动切换通道配色（Tek 系列为黄/蓝/粉/绿；Keysight 系列为黄/绿/蓝/粉；未连接时为统一灰色）。
- **Apply 脏标记**：参数修改后 Apply 按钮变紫色，未点击不会下发到仪器；轮询回读不会覆盖未 Apply 的本地值。
- **Mock 模式**：`DEBUG_MOCK=True` 时自动连接 MockMSO64B。
- **测量轮询间隔**：默认 0.5 秒，过于频繁会增加 VISA 通信负载。
- **状态轮询**：连接后每 1 秒回读一次通道/时基/触发状态，与本地未 Apply 的输入冲突时优先保留本地输入。
- **AI 集成**：本页面已注册 `ai_capabilities`，AI 助手可读取当前配置与测量结果。
