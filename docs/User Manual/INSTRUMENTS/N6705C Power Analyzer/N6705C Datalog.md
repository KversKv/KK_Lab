# N6705C Datalog

N6705C Datalog 是基于 PySide6 + pyqtgraph 的**长时间数据采集与波形分析**页面，支持 N6705C 实时采集、外部文件导入、多通道叠加波形、Marker 区间分析与统计指标导出。

## 页面入口

- 导航栏 → `INSTRUMENTS` → `N6705C` → 子菜单 `N6705C Datalog`
- 对应源码：`ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py`
- 也可独立运行调试：`python ui\pages\n6705c_power_analyzer\n6705c_datalog_ui.py`（独立窗口标题 `N6705C Datalog - Debug`，默认 1400×900）

## 界面布局

### 1. 标题栏
页面标题 `Keysight N6705C Datalog Analyzer` + 副标题说明。

### 2. 左侧侧边栏 — Instrument Connection（仪器连接）
- 点击左侧垂直文字按钮 `Instrument Connection` 展开/折叠。
- **设备搜索**：扫描局域网内的 N6705C 设备。
- **手动添加**：点击 `⋯` 菜单 → `Add Instrument Manually`，支持 TCPIP / GPIB。
- **设备卡片**：型号 / 序列号 / IP，每张卡片带 Connect / Disconnect。
- **设备插槽 A/B/C/D**：右键插槽可断开。
- 连接状态与 `n6705c_top` 共享，Analyser 页连过的设备在此页直接可见。

### 3. 左侧配置区
**DATALOG CONFIG（采集配置）**

| 参数 | 单位 | 默认 | 说明 |
|---|---|---|---|
| Sampling Period | μs | 20 | 采样周期 |
| Monitoring Time | s | 5 | 监控时长 |
| Minimum | 复选 | 关 | 勾选后自动使用仪器支持的最小采样周期 |

**Measurement Settings（统计指标勾选）**
- Minimum / Average（默认勾选）/ Maximum（默认勾选）
- Peak to Peak
- Charge (Ah) / Energy (Wh)
- Charge (C) / Energy (J)

> 统计指标决定下方分析表中显示哪些列；放置 Marker A/B 后，统计结果会限定在 [A, B] 区间内。

**操作按钮**
- `Start Recording` / `Stop Recording`：开始 / 停止采集
- `Export Datalog`：导出已采集数据
- `Import Datalog`：导入外部数据文件（CSV / DLOG / EDLG）

### 4. 中央 — Datalog Viewer（波形图）
- 多通道叠加波形，每个通道独占一个纵向 band，通道间虚线分隔。
- 左侧通道名标签可双击重命名。
- X 轴为时间（秒），支持鼠标拖拽缩放与平移。

**图表工具栏**
- `Reset View`：重置视图范围。
- `Box Zoom`：框选缩放模式（4 秒后自动关闭）。
- `Set Marker A` / `Set Marker B`：放置区间标记线。
- `Clear Markers`：清除所有标记。
- `Time Offset`：对仪器 B 的波形做时间偏移对齐（仅双仪器模式可见）。

### 5. 右侧 — Channel Config（通道配置）
**Active 标签页**：列出已连接仪器的全部通道，每个通道可独立勾选测量类型：
- **I**（电流）
- **V**（电压）
- **P**（功率 = V × I）

每通道还有 `Scale`（缩放）与 `Offset`（偏移），可手动调整波形显示。

**导入文件标签页**：导入的文件以独立标签页显示其通道列表，标签可关闭。

### 6. 底部 — 分析表 / 标注 / 自定义标签
- **Measurement 分析表**：按 Measurement Settings 勾选项展示各通道统计值；Marker A/B 存在时仅统计区间内数据。
- **Label 标注**：选择通道 → 输入时间点 → 输入文字 → 点击 `+`，标注显示在波形对应位置。

## 典型操作流程

### 流程一：实时采集并分析
1. 在 Instrument Connection 面板连接至少一台 N6705C。
2. 在右侧 Channel Config → Active 勾选需要采集的通道及 I/V/P 类型。
3. 设置 Sampling Period 与 Monitoring Time。
4. 点击 `Start Recording`，进度条显示采集进度。
5. 采集完成波形自动绘制。
6. 在 Measurement Settings 勾选需要的统计指标 → 分析表自动刷新。
7. 放置 Marker A、B → 统计表切换为区间内统计。
8. 点击 `Export Datalog` 保存数据。

### 流程二：导入外部数据
1. 点击 `Import Datalog` 选择文件（支持 .csv / .dlog / .edlg）。
2. 导入文件以新标签页出现在 Channel Config 右侧。
3. 勾选要显示的通道，波形立即绘制。

### 流程三：双仪器对比
1. A、B 插槽各连接一台 N6705C。
2. 在 Channel Config 同时勾选两台仪器的通道。
3. 如两台时钟未对齐，使用工具栏 `Time Offset` 调整 B 仪器波形的时间偏移。

## 关键参数说明

| 参数 | 单位 | 默认 | 说明 |
|---|---|---|---|
| Sampling Period | μs | 20 | 越小采样越密，但占用仪器内存越大 |
| Monitoring Time | s | 5 | 采集总时长，达时自动停止 |
| Scale | — | 1 | 波形纵向缩放系数 |
| Offset | — | 0 | 波形纵向偏移量 |

## 注意事项

- **采样周期下限**：N6705C 实际最小采样周期受机型限制；勾选 `Minimum` 自动用仪器支持的最小值。
- **导入文件命名约定**：通道标签解析支持 `F<N>-<slot>-<type><num>` 前缀（如 `F1-A-I1`），用于多文件合并显示。
- **Marker 区间统计**：Marker A/B 须都存在才生效；只放一个 Marker 不会改变统计区间。
- **时间偏移**：双仪器模式下两台 N6705C 内部时钟独立，需用 `Time Offset` 手动对齐。
- **导出格式**：导出文件含通道名、时间戳、采样值，便于二次分析。
- **Mock 模式**：`DEBUG_MOCK=True` 时自动连接 MockN6705C，可走通采集流程（数据为模拟随机值）。
