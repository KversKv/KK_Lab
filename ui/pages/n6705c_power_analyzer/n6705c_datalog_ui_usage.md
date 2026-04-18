# N6705C Datalog UI 使用说明

## 概述

`n6705c_datalog_ui.py` 是一个基于 PySide6 + pyqtgraph 的图形化界面工具，用于对 **Keysight N6705C 直流电源分析仪**进行数据采集（Datalog）、波形查看、数据分析和导入/导出操作。

---

## 启动方式

### 独立运行

```bash
python d:\CodeProject\TRAE_Projects\KK_Lab\ui\pages\n6705c_power_analyzer\n6705c_datalog_ui.py
```

直接运行时会打开一个独立窗口（标题为 "N6705C Datalog - Debug"，默认分辨率 1400×900）。

### 作为子页面嵌入

在主程序中通过 `N6705CDatalogUI` 类实例化并嵌入到其他 UI：

```python
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import N6705CDatalogUI

widget = N6705CDatalogUI(n6705c_top=top_instance)
```

传入 `n6705c_top` 参数可以从上层页面同步已连接的仪器状态。

---

## 界面布局

界面由以下几个主要区域组成：

### 1. 标题栏
显示页面标题 "Keysight N6705C Datalog Analyzer" 和副标题说明。

### 2. 左侧侧边栏 —— Instrument Connection（仪器连接面板）
- 点击左侧 **"Instrument Connection"** 垂直文字按钮展开/折叠。
- **设备搜索**：点击搜索按钮自动扫描局域网内的 N6705C 设备。
- **手动添加仪器**：点击 "⋯" 菜单 → "Add Instrument Manually"，支持 TCPIP 和 GPIB 两种连接方式。
- **设备卡片**：扫描到的设备以卡片形式显示，包含型号、序列号、IP 地址。每张卡片有 Connect / Disconnect 按钮。
- **设备插槽 (A/B/C/D)**：已连接的设备会被分配到插槽。右键插槽可执行断开操作。

### 3. 左侧面板 —— 配置区域

#### DATALOG CONFIG（采集配置）
| 参数 | 说明 | 默认值 |
|------|------|--------|
| Sampling Period (μs) | 采样周期，单位微秒 | 20 |
| Monitoring Time (s) | 监控时长，单位秒 | 5 |
| Minimum 复选框 | 勾选后自动使用最小采样周期 | 未勾选 |

#### Measurement Settings（测量设置）
可以勾选需要在分析表格中显示的统计指标：
- Minimum（最小值）
- Average（平均值）- 默认勾选
- Maximum（最大值）- 默认勾选
- Peak to Peak（峰峰值）
- Charge (Ah) / Energy (Wh)（电荷/能量，Ah/Wh 单位）
- Charge (C) / Energy (J)（电荷/能量，C/J 单位）

#### 操作按钮
- **Start Recording / Stop Recording**：开始或停止数据采集。
- **Export Datalog**：导出已采集的数据。
- **Import Datalog**：导入外部数据文件。

### 4. 中央区域 —— Datalog Viewer（波形图表）
- 使用 pyqtgraph 绘制多通道叠加波形。
- 每个通道显示在独立的纵向分区（band）中，通道之间以虚线分隔。
- 左侧显示通道名称标签（可双击重命名）。
- X 轴为时间轴（秒），支持鼠标拖拽缩放。

#### 图表工具栏
- **Reset View**：重置视图范围。
- **Box Zoom**：框选缩放模式（4 秒后自动关闭）。
- **Set Marker A / Marker B**：在图表上放置标记线 A、B 用于区间分析。
- **Clear Markers**：清除所有标记。
- **Time Offset**：对仪器 B 的波形进行时间偏移对齐（仅在双仪器模式下可见）。

### 5. 右侧面板 —— Channel Config（通道配置）

#### Active 标签页
显示已连接仪器的通道，每个通道可独立开关以下测量类型：
- **I**（电流）
- **V**（电压）
- **P**（功率）= 电压 × 电流

每个通道还有 **Scale**（缩放）和 **Offset**（偏移）参数，可手动输入调整波形显示范围。

#### 导入文件标签页
导入的文件会以独立标签页显示其通道列表，标签页可关闭。

### 6. 底部区域 —— Measurement 分析表 / Label 标注 / 自定义标签

#### Measurement 分析表
当存在数据时，自动显示各通道的统计值表格（根据 Measurement Settings 中的勾选项）。
放置 Marker A 和 Marker B 后，分析结果限定在标记区间内。

#### Label 标注
可在波形上添加自定义文字标注：
- 选择通道
- 输入时间点
- 输入标注文字
- 点击 "+" 添加，标注会显示在图表上对应位置

---

## 核心功能

### 数据采集（Recording）

1. 连接至少一台 N6705C 仪器。
2. 在 Channel Config 中勾选需要采集的通道和测量类型（I / V / P）。
3. 设置采样周期和监控时长。
4. 点击 **Start Recording**。
5. 采集过程中会显示进度条。
6. 采集完成后波形自动绘制在图表中。

### 双仪器模式（8 通道）

- 连接两台 N6705C（分别分配到插槽 A 和 B），可同时采集 8 个通道。
- 通道名称自动加前缀 `A-` 或 `B-`。
- 可通过 **Time Offset** 功能对仪器 B 的波形进行时间偏移，用于对齐两台仪器的时间基准。
- 支持通过 Marker A/B 自动计算偏移量。

### Marker 标记与区间分析

1. 点击 **Set Marker A** 然后在图表上点击放置标记线 A。
2. 同理放置标记线 B。
3. 标记线之间区域高亮显示。
4. 分析表自动计算标记区间内的统计值。
5. 标记线支持拖拽移动。

### 通道波形交互

- **点击通道区域**：选中该通道（高亮显示其 band 区域）。
- **鼠标拖拽**：在选中通道内上下拖拽调整偏移。
- **鼠标滚轮**：在选中通道内滚轮缩放该通道的纵向比例。
- **鼠标悬停**：显示十字线和 Tooltip，展示各通道在当前时间点的数值。

---

## 数据导入/导出

### 导入

点击 **Import Datalog** 按钮，支持以下格式：

| 格式 | 说明 |
|------|------|
| `.csv` | 标准 CSV 格式，首列为时间，后续列为各通道数据。支持附带 `[CUSTOM_LABELS]` 和 `[CH_NAME_RENAMES]` 段。 |
| `.dlog` | Keysight 原始二进制 Datalog 格式。 |
| `.edlg` | Keysight 扩展 Datalog 格式。 |

导入的文件数据以 `F1-`、`F2-` 等前缀与实时采集数据区分，每个导入文件在 Channel Config 中有独立的标签页。

### 导出

点击 **Export Datalog** 按钮，支持导出为：

| 格式 | 说明 |
|------|------|
| `.csv` | 包含时间列和所有通道数据。双仪器模式下分 `Time_A(s)` 和 `Time_B(s)` 两组时间列。同时导出自定义标注和通道重命名信息。 |
| `.dlog` | 导出原始二进制 Datalog 数据（需先有采集或导入的原始数据）。 |

---

## 调试模式

当 `debug_config.py` 中 `DEBUG_MOCK = True` 时：
- 自动添加模拟设备，无需真实仪器即可测试 UI。
- 采集操作会生成模拟的随机数据。

---

## 依赖

| 依赖 | 说明 |
|------|------|
| PySide6 | Qt for Python，UI 框架 |
| pyqtgraph | 高性能图表库 |
| pyvisa | VISA 仪器通信 |
| instruments.power.keysight.n6705c | N6705C 仪器驱动 |
| instruments.power.keysight.n6705c_datalog_process | 数据解析与处理工具函数 |

---

## 主要类说明

| 类名 | 说明 |
|------|------|
| `N6705CDatalogUI` | 主界面 Widget，包含所有 UI 逻辑和仪器控制 |
| `_ScanWorker` | 后台线程 Worker，用于扫描局域网内的 N6705C 设备 |
| `_ConnectWorker` | 后台线程 Worker，用于连接指定仪器 |
| `_DatalogWorker` | 后台线程 Worker，执行数据采集（配置、启动、等待、读取数据） |
| `VerticalTextButton` | 可折叠面板的垂直文字按钮控件 |
| `CardFrame` | 带标题和图标的卡片式容器 |
| `ChannelNameLabel` | 可编辑的通道名称标签（双击重命名） |
| `ToggleLabel` | 可点击切换的标签控件 |
| `ScaleOffsetEdit` | 禁用鼠标滚轮的 QLineEdit，用于 Scale/Offset 输入 |

---

## 快捷操作一览

| 操作 | 说明 |
|------|------|
| 鼠标左键点击波形区域 | 选中对应通道 |
| 鼠标左键拖拽（选中通道） | 上下偏移通道波形 |
| 鼠标滚轮（选中通道） | 缩放通道纵向比例 |
| 鼠标左键拖拽标记线 | 移动 Marker A / B |
| 鼠标悬停波形 | 显示十字线 + 各通道数值 Tooltip |
| 双击通道名称 | 重命名通道 |
| 右键点击插槽 | 弹出断开连接菜单 |
