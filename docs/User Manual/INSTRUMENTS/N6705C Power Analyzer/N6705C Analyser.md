# N6705C Analyser

N6705C Analyser 是 Keysight N6705C 直流电源分析仪的**实时控制台**，用于通道级电压/电流配置、输出开关、批量自动设置与功耗读取。

## 页面入口

- 导航栏 → `INSTRUMENTS` → `N6705C` → 子菜单 `N6705C Analyser`
- 对应源码：`ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py`

## 界面布局

页面由三个视图（通过页面顶部隐式切换）组成，由 `SettingViewMixin` / `BatchViewMixin` / `ConsumptionViewMixin` 三个 Mixin 提供：

### 1. Setting View（设置视图，默认）
- **顶部连接区**：A/B 两个插槽各自的搜索按钮、VISA 资源下拉、Connect/Disconnect 按钮、连接状态指示。
- **通道标签栏**（ChannelTabBar）：1~4 通道标签 + 主题色，点击切换当前通道。
- **当前通道控制面板**：
  - Voltage (V) 输入框
  - Current (A) 输入框
  - Output ON/OFF 拨动开关
  - Mode 选择（CV / CC 等指示，从仪器回读）
  - 实测电压/电流/功率读数（每秒轮询刷新）
- **Apply 按钮**：脏数据标记（输入未应用时按钮高亮紫色），点击后下发到仪器。

### 2. Batch View（批量视图）
- 列出全部通道（A/B 两台最多 8 个通道）的电压、电流、输出状态。
- **Auto Set**：测量当前电压并对齐到 50mV 网格（含特殊电压），设电流限值并打开输出。
- **Auto Set (+20mV)**：测当前电压后 +20mV 设为目标，再开输出。
- 支持批量编辑后一次 Apply。

> 这两个按钮已注册为 AI 可触发的具名 UI 动作 `power_analyser.auto_set` / `power_analyser.auto_set_20mv`，风险等级 `high`，触发前 AI 会请求确认，且要求至少一台 N6705C 已连接。

### 3. Consumption View（功耗视图）
- 卡片式显示各通道实时电流/功率，常用于芯片功耗快速读数。

## 典型操作流程

### 流程一：单通道设置并测量
1. 在 A 插槽点击 **🔍 搜索** → 等待设备列表填充 → 选中目标 N6705C → 点击 **Connect**。
2. 状态变为绿色 `● Connected`，通道标签栏出现该设备的 1~4 通道。
3. 点击通道标签 1。
4. 在 Voltage 输入 `3.3`，Current 输入 `0.5`，点击 **Apply**。
5. 拨开 Output 开关，仪器开始输出。
6. 实测区每秒回读电压/电流/功率。

### 流程二：批量 Auto Set
1. 至少连接一台 N6705C。
2. 切到 Batch View。
3. 检查/修改批量目标电压列。
4. 点击 **Auto Set**（或 **Auto Set (+20mV)**）。
5. 弹出确认对话框 → 确认后自动测电压、对齐网格、设限流、开输出。

### 流程三：双仪器对比
1. A 插槽连接一台 N6705C，B 插槽连接另一台。
2. 切换 `Dual Mode` 后可同步控制两台仪器的同号通道。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Voltage | V | 通道输出电压设置值 |
| Current | A | 通道电流限值（OCP） |
| 实测 V / I / P | V / A / W | 每秒轮询回读的实际输出 |
| Channel | 1~4 | 单台 N6705C 的物理通道号 |

## 注意事项

- **Apply 按钮状态**：输入框修改未 Apply 时按钮变紫色高亮，提醒有未下发设置；刷新轮询不会覆盖未 Apply 的本地输入。
- **连接失败**：状态显示 `Connection failed`，按钮恢复可用，可重试；常见原因是 VISA 资源被其他进程占用或 IP 不可达。
- **Mock 模式**：`DEBUG_MOCK=True` 时自动连接两台 MockN6705C（资源名 `MOCK::N6705C::A/B`），用于无硬件调试。
- **AI 触发 Auto Set**：会被标记为高风险动作，AI 调用前需用户确认；未连接仪器时该动作在 AI 列表中不显示（不盲点）。
- **避免硬编码地址**：所有 VISA 地址均来自下拉框或搜索结果，不写入代码。
