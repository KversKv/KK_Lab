# Consumption Test 汇总

> 本文件汇总当前 `consumption_test` 页面 **完整 UI 结构与组件**、**Config Import** 区域细节,以及 **Auto Test** 完整测试逻辑,附带 ASCII 示意图便于直观理解。
>
> 代码事实源:
> - UI 主文件: [ui/pages/consumption_test/consumption_test.py](../../ui/pages/consumption_test/consumption_test.py)
> - UI 布局 Mixin: [ui/pages/consumption_test/view_panels.py](../../ui/pages/consumption_test/view_panels.py)
> - UI 配置 Mixin: [ui/pages/consumption_test/view_config.py](../../ui/pages/consumption_test/view_config.py)
> - 自定义控件: [ui/pages/consumption_test/widgets.py](../../ui/pages/consumption_test/widgets.py)
> - Worker: [core/consumption_test/workers/auto_test_worker.py](../../core/consumption_test/workers/auto_test_worker.py)
> - Worker: [core/consumption_test/workers/force_worker.py](../../core/consumption_test/workers/force_worker.py)
> - Common: [core/consumption_test/workers/common.py](../../core/consumption_test/workers/common.py)

---

## 一、页面整体布局总览

### 1.1 顶层结构示意图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Header: [⚡] Consumption Test          [Import Config] [Export Config]       │
│  (icon 22x22)  (pageTitle)            (右上角两个 JSON 导入/导出按钮)         │
├──────────────────────────────────────────────────────────────────────────────┤
│  Config Import 面板(横跨整个宽度,见 §二)                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌─────────────────────────────────────────────────────┐ │
│  │ 左列(320px固定 │  │ 右列(Expanding)                                     │ │
│  │  宽,可垂直滚动)│  │                                                      │ │
│  │                │  │  Channel Config 区域(横向滚动卡片,见 §七)            │ │
│  │  Connection    │  │  Test Buttons Row(START TEST / Auto Test,见 §八)   │ │
│  │  Panel(§三)    │  │  Consumption Test Panel(结果卡片+BIN 表,见 §九)     │ │
│  │  Firmware      │  │                                                      │ │
│  │  Download(§四) │  │                                                      │ │
│  │  Test Config   │  │                                                      │ │
│  │  (§五)         │  │                                                      │ │
│  │  (stretch)     │  │                                                      │ │
│  └────────────────┘  └─────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│  ExecutionLogsFrame(QSplitter 隐式手柄, 上 body / 下 logs,见 §十)            │
│  [Clear Log] [log_edit...]                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 主布局参数

| 项 | 值 |
|---|---|
| 根 Layout | `QVBoxLayout(self)` |
| ContentsMargins | `(16, 12, 16, 12)` |
| Spacing | `12` |
| 左列宽 | `320px` 固定(`QScrollArea.setFixedWidth`) |
| 左列滚动 | 垂直 AsNeeded,水平 AlwaysOff |
| 主体分割器 | `ExecutionLogsFrame.wrap_with(body, show_progress=False, stretch=(1,0), sizes=[600,120], min_log_height=40)` |
| 启动钩子 | `QTimer.singleShot(0, self._on_mcu_search)` 首次打开自动搜 MCU 串口 |

---

## 二、Config Import 区域(顶部横跨)

### 2.1 区域整体示意图

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  [📄] Config Import   [High V│Std V]  Chip  [──chip──▼] [Check]                  │
│  (16x16)  (12px bold)  ↑ BinaryTextToggle  ↑ DarkComboBox  ↑ 60x22              │
│                         150x24,初始 High V    22px,Expanding   触发 I2C chip check│
├──────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│  │ Vcore   │ │ VcoreM  │ │ VcoreL  │ │ VANA    │ │ VHPPA   │  ← 各列 rail_label │
│  │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │  (10px #7e96bf)    │
│  │ │YAML │ │ │ │YAML │ │ │ │YAML │ │ │ │YAML │ │ │ │YAML │ │  QPlainTextEdit    │
│  │ │edit │ │ │ │edit │ │ │ │edit │ │ │ │edit │ │ │ │edit │ │  70~110px 高        │
│  │ └─────┘ │ │ └─────┘ │ │ └─────┘ │ │ └─────┘ │ │ └─────┘ │  Consolas 10px      │
│  │[Import] │ │[Import] │ │[Import] │ │[Import] │ │[Import] │  灰底 #162544       │
│  │[Exec ]  │ │[Exec ]  │ │[Exec ]  │ │[Exec ]  │ │[Exec ]  │  紫底 #5d45ff       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  各 22px,10px       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 容器与布局参数

| 项 | 值 |
|---|---|
| 容器 | `QFrame#configPanel` |
| 背景 | `#0b1630` |
| 边框 | `1px solid #18284d` |
| 圆角 | `12px` |
| 内部 Layout | `QVBoxLayout` |
| ContentsMargins | `(12, 10, 12, 10)` |
| Spacing | `6` |
| 电源轨常量 | `_RAIL_NAMES = ["Vcore", "VcoreM", "VcoreL", "VANA", "VHPPA"]` |

### 2.3 顶行组件(标题 + 测试模式 + Chip + Check)

QHBoxLayout, spacing=8。

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `config_icon_label` | QLabel | 16×16,file-json.svg,tint `#94a3b8` |
| `config_title` | QLabel | "Config Import",12px bold,`#ffffff` |
| `test_mode_toggle` | BinaryTextToggle | 150×24,left=`high_voltage`("High V"),right=`standard`("Std V"),初始 `high_voltage` |
| `chip_label` | QLabel | "Chip",10px,`#7e96bf` |
| `chip_combo` | DarkComboBox | 22px 高,Ignored/Expanding;首项 "-- Select Chip --",余项 `SUPPORTED_CHIPS` |
| `chip_check_btn` | QPushButton | "Check",60×22,11px,灰底 `#162544`,hover `#1c315b`;触发 I2C chip check |

**测试模式语义**(`test_mode_toggle.value()`):

| 模式 key | 显示 | UI 影响 | Auto Test 行为 |
|---|---|---|---|
| `high_voltage` | High V | Channel Config 卡片显示 Force mode toggle + force/auto stack | 跳过 I2C 配置(should_config=False),直接走 Force Vol 参数 |
| `standard` | Std V | 隐藏 Channel Config 卡片的 Force mode toggle + force/auto stack | 走 I2C 配置流程,按启用通道 Name 匹配对应电源轨配置 |

> 原 `force_config_cb` 复选框已移除,语义被 `test_mode_toggle` 取代。
> 原 `saved_config_combo`(Config 下拉)已移除,每轨配置直接存 `<chip>.yaml` 顶层 rail key 下。

### 2.4 中部 5 列电源轨(横向 QHBoxLayout, spacing=6)

每列结构一致,以 `Vcore` 为例:

```
┌─────────────────┐
│  Vcore          │  ← rail_label: QLabel 10px #7e96bf
├─────────────────┤
│  Vcore config...│
│                 │  ← QPlainTextEdit (70~110px 高)
│                 │     placeholder "{rail} config..."
│                 │     Consolas 10px, border #25355c, focus #5d45ff
├─────────────────┤
│ [Import] [Exec] │  ← rail_btn_row: QHBoxLayout(spacing=3)
└─────────────────┘
```

| 组件字典 | 类型 | 说明 |
|---|---|---|
| `_rail_config_edits[rail]` | QPlainTextEdit | 该轨 YAML 文本框 |
| `_rail_import_btns[rail]` | QPushButton | "Import",灰底 `#162544`,upload.svg 12px,22px 高,10px |
| `_rail_exec_btns[rail]` | QPushButton | "Exec",紫底 `#5d45ff`,settings.svg 12px,22px 高,10px |

### 2.5 信号连接

```python
chip_combo.currentIndexChanged      -> _on_chip_selected          # 加载 <chip>.yaml 各 rail 配置
chip_check_btn.clicked              -> _on_chip_check
test_mode_toggle.toggled            -> _on_test_mode_changed      # 切换 Channel Config 卡片 Force 控件显隐
_rail_import_btns[rail].clicked     -> _import_rail_configuration(rail)   # 仅保存该轨到 <chip>.yaml
_rail_exec_btns[rail].clicked       -> _execute_rail_configuration(rail)  # 仅下发该轨 I2C 配置
```

### 2.6 每轨 Import / Exec 行为

**Import**(`_import_rail_configuration(rail_name)`):
1. 检查 chip 已选 + 该轨文本框非空;
2. 调 `_update_chip_rail_yaml(chip_name, rail_name, config_text)`:
   - 读 `chips/bes_chip_configs/main_chip_configs/<chip>.yaml`(若存在);
   - **仅更新该 rail 的顶层 key**(其它 rail key 和非 rail key 保留);
   - 用 `yaml.safe_dump` 写回(sort_keys=False, allow_unicode=True)。
3. YAML 顶层结构示例:
   ```yaml
   Vcore:
     - WRITE 0x100 0x1
     - WRITE_BITS 0x110 7 0 0x3
   VANA:
     - WRITE 0x200 0x2
   ```

**Exec**(`_execute_rail_configuration(rail_name)`):
1. 检查 chip 已选 + 该轨文本框非空;
2. 仅解析该轨文本框为 `config_commands`(不合并其它轨);
3. I2CInterface.initialize() + bes_chip_check();
4. `_compare_chip_info` 校验;
5. `_run_config_commands` 下发该轨 WRITE/WRITE_BITS/READ;
6. **不触碰**其它 rail 配置,**也不**修改 N6705C 通道设置。

### 2.7 Chip 选择时的 YAML 加载(`_on_chip_selected` → `_load_rail_configs_from_chip`)

```
1. chip_combo.currentIndex <= 0
   → 清空所有 rail 文本框,返回
2. 读取 chips/bes_chip_configs/main_chip_configs/<chip>.yaml
   - 文件不存在 → 各 rail 留空,日志提示
   - PyYAML 未装 → 各 rail 留空,警告
   - 解析失败 → 各 rail 留空,警告
3. 顶层 key 与 _RAIL_NAMES 大小写不敏感匹配
   - 值为 list → "\n".join 拼接
   - 值为 str → 直接使用
   - 其它 → str(val)
   → 填入对应 rail 文本框
4. 日志: "Loaded N/5 rail configs for <chip> from YAML."
```

---

## 三、Connection Panel(N6705C A/B)

> 代码事实源: [view_panels.py `_create_connection_panel`](../../ui/pages/consumption_test/view_panels.py)

### 3.1 示意图

```
┌─────────────────────────────────┐
│  ┌───────────────────────────┐  │
│  │ N6705C A       ● Disconnected │  ← tag(#00f5c4) + status_label
│  │ [TCPIP0::K-N6705C-...▼]      │  ← visa_combo DarkComboBox 24px
│  │ [🔍 search] [Connect]         │  ← SpinningSearchButton + connect_btn 24px
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ N6705C B       ● Disconnected │  ← tag(#f2994a)
│  │ [TCPIP0::K-N6705C-03845...▼] │  ← 默认资源预填
│  │ [🔍 search] [Connect]         │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 3.2 组件

| 组件 | 类型 | 说明 |
|---|---|---|
| `_n6705c_conn_widgets[label]` | dict | 含 `tag`/`status`/`combo`/`search_btn`/`connect_btn` |
| `visa_combo` | DarkComboBox | 24px,Expanding;预填默认 VISA 资源(A 默认 K-N6705C-06098,B 默认 K-N6705C-03845) |
| `search_btn` | SpinningSearchButton | 24×24,搜索设备时旋转动画 |
| `connect_btn` | QPushButton | 24px,由 `update_connect_button_state` 控制 Connect/Disconnect 文案与配色 |
| `_tag_colors` | — | A=`#00f5c4`,B=`#f2994a` |

容器:`QFrame#connectionPanel`,背景 `#0b1630`,边框 `1px solid #18284d`,圆角 12px;每个 N6705C 一张子卡片 `QFrame#connSub{A\|B}`。

### 3.3 信号连接

```python
search_btn.clicked  -> _on_device_search(label)         # 搜索 VISA 设备
connect_btn.clicked -> _on_device_connect_or_disconnect(label)
```

### 3.4 状态属性

| 属性 | 含义 |
|---|---|
| `is_connected_a` / `is_connected_b` | N6705C A/B 连接状态 |
| `_disabled_overlay` | 未连接时覆盖在 Consumption Test Panel 上的遮罩(半透明) |

---

## 四、Firmware Download Panel

> 代码事实源: [view_panels.py `_create_firmware_panel`](../../ui/pages/consumption_test/view_panels.py)

### 4.1 示意图

```
┌─────────────────────────────────┐
│  Firmware Download              │  ← fw_title 12px bold white
│  COM: [──COM port──▼] [🔍]      │  ← _build_firmware_serial_widgets
│  Mode [Flash│RAM Run]           │  ← download_mode_toggle DownloadModeToggle 140px
│  [No file selected...    ] [...] │  ← firmware_file_input + firmware_browse_btn 36px
│  [ ▶ Download         ]          │  ← download_btn ProgressButton
└─────────────────────────────────┘
```

### 4.2 组件

| 组件 | 类型 | 说明 |
|---|---|---|
| `serial_label` / `serial_combo` / `serial_search_btn` | QLabel / DarkComboBox / SpinningSearchButton | 串口选择行 |
| `download_mode_toggle` | DownloadModeToggle | 140px 宽;Flash / RAM Run 切换 |
| `firmware_file_input` | QLineEdit | 只读,显示固件路径 |
| `firmware_browse_btn` | QPushButton | "...",36px 宽,紫底 `#5d45ff` |
| `download_btn` | ProgressButton | 带进度/Stop 双信号 |

### 4.3 信号连接

```python
firmware_browse_btn.clicked -> _browse_firmware
download_btn.clicked        -> _download_to_dut
download_btn.stop_clicked   -> _stop_download
```

### 4.4 固件多 BIN 支持

`firmware_paths`(list)可含 programmer.bin + app.bin,Auto Test 按每个 BIN 循环测试。

---

## 五、Test Config Panel

> 代码事实源: [view_config.py `_create_test_config_panel`](../../ui/pages/consumption_test/view_config.py)

### 5.1 示意图

```
┌──────────────────────────────────────────┐
│  [🔧] Test Config                        │  ← cfg_icon + cfg_title 12px bold
├──────────────────────────────────────────┤
│  Test Time (s) [  10  ]                  │  ← test_time_input QLineEdit 24px
│  Control       [N6705C│MCU]               │  ← control_method_toggle ControlMethodToggle 140px
│  MCU           [YD-RP2040▼] (MCU 模式可见)│  ← mcu_type_combo(默认 CH9114F)
│  COM           [──MCU COM──▼] [🔍]        │  ← mcu_port_combo + mcu_search_btn
│                ● Disconnected [Connect]   │  ← mcu_status_label + mcu_connect_btn 88px
│  PwrON         [──B-CH1──▼] [↑↓]          │  ← poweron_channel_combo + poweron_polarity_toggle
│  Reset [x]     [──B-CH2──▼] [↑↓]          │  ← reset_enable_cb + reset_channel_combo + reset_polarity_toggle
└──────────────────────────────────────────┘
```

### 5.2 组件

| 组件 | 类型 | 说明 |
|---|---|---|
| `test_time_input` | QLineEdit | "10",24px,居中,测试时长(秒) |
| `control_method_toggle` | ControlMethodToggle | 140px;`N6705C` / `MCU` 切换,显隐 MCU 行 |
| `mcu_type_combo` | DarkComboBox | YD-RP2040 / CH9114F(默认) |
| `mcu_port_combo` | DarkComboBox | "Select MCU COM..."/"Select CH9114F COM..." |
| `mcu_search_btn` | SpinningSearchButton | 24×24 |
| `mcu_status_label` | QLabel | "● Disconnected" |
| `mcu_connect_btn` | QPushButton | "Connect",88×24,绿底 `#053b38` |
| `poweron_channel_combo` | DarkComboBox | 默认 B-CH1 |
| `poweron_polarity_toggle` | PolarityToggle | rising/falling |
| `reset_enable_cb` | QCheckBox | 启用 RESET 通道(未勾选则跳过 RESET) |
| `reset_channel_combo` | DarkComboBox | 默认 B-CH2 |
| `reset_polarity_toggle` | PolarityToggle | rising/falling |

容器:`QFrame#testConfigPanel`,背景 `#0a1228`,边框 `1px solid #1a2d57`,圆角 12px;内部 `QGridLayout`。

### 5.3 Control Method 切换逻辑(`_on_control_method_changed`)

| 模式 | 可见控件 |
|---|---|
| `N6705C`(默认) | PwrON/RESET 通道下拉(选项为 N6705C 通道);MCU 行隐藏 |
| `MCU` | MCU 类型/COM/状态/Connect 行可见;PwrON/RESET 改为 GPIO0/GPIO1 选项 |

切换时通过 `_saved_control_channels` 保留各自模式的上次通道选择。

### 5.4 Reset Enable 逻辑(`_on_reset_enable_toggled`)

未勾选时 `reset_channel_combo` / `reset_polarity_toggle` 禁用;Auto Test 中 RESET 步骤被跳过。

### 5.5 信号连接

```python
mcu_search_btn.clicked            -> _on_mcu_search
mcu_connect_btn.clicked           -> _on_mcu_connect_or_disconnect
mcu_type_combo.currentIndexChanged -> _on_mcu_type_changed
control_method_toggle.toggled     -> _on_control_method_changed
reset_enable_cb.toggled           -> _on_reset_enable_toggled
```

---

## 六、Channel Config 区域(容器 + 卡片)

> 代码事实源: [view_config.py `_create_channel_config_section` + `_add_channel_config_card`](../../ui/pages/consumption_test/view_config.py)

### 6.1 区域容器

```
┌──────────────────────────────────────────────────────────────────┐
│  [⚙] Channel Config                                              │  ← cfg_title 13px bold
├──────────────────────────────────────────────────────────────────┤
│  ←(横向滚动) [card0][card1][card2]...[+ Add]                     │  ← scroll_area 200px 高
└──────────────────────────────────────────────────────────────────┘
```

| 项 | 值 |
|---|---|
| 容器 | `QFrame#testConfigFrame` |
| 背景 | `#0a1228`,边框 `1px solid #1a2d57`,圆角 12px |
| 滚动区 | `QScrollArea` 200px 高,水平 AsNeeded,垂直 AlwaysOff |
| 内部容器 | `QWidget#channelConfigContainer`,QHBoxLayout,末尾 addStretch() |

### 6.2 单张卡片结构(以 Vcore 通道为例)

```
┌───────────────────────────────────┐
│  [x] Enable                [✕]    │  ← top_row: Enable QCheckBox + remove_btn
├───────────────────────────────────┤
│  Name  [──────── Vcore ───────▼]  │  ← name_row: QLabel(72px) + DarkComboBox
├───────────────────────────────────┤
│  CH    [──────── A-CH2 ───────▼]  │  ← ch_row: QLabel(72px) + DarkComboBox
├───────────────────────────────────┤
│  [  Force  │  Auto  ]              │  ← force_mode_toggle BinaryTextToggle 140x22
│        (当前:Auto)                 │     (high_voltage 模式可见; standard 模式隐藏)
├───────────────────────────────────┤
│  ┌──── Force 模式可见(Page 0)──┐  │  ← force_auto_stack QStackedLayout
│  │  [──────── V (Force) ──────] │  │     - force_value_input QLineEdit
│  └──────────────────────────────┘  │       (high_voltage 模式可见; standard 隐藏)
│  ┌──── Auto 模式可见(Page 1)───┐  │
│  │  Boost Mode                  │  │     - boost_mode_label + boost_mode_toggle
│  │  [  Const  │   Pct  ]        │  │     - boost_value_input QLineEdit
│  │  [────── boost value ──────] │  │       (同上,随 stack_container 显隐)
│  └──────────────────────────────┘  │
└───────────────────────────────────┘

卡片: 宽 160px (fixed), 最小高 220px
内部 QVBoxLayout: margins=(10,8,10,8), spacing=5
```

### 6.3 每通道数据契约

```python
{
  "name": "Vcore",
  "channel": "A-CH2",
  "enabled": True,
  "force_mode": "auto",          # "force" / "auto"  (默认 "auto")
  "force_value": "",             # Force 模式下用户输入电压(V)
  "boost_mode": "constant",      # "constant" / "percent"  (Auto 模式默认)
  "boost_value": "0.02",         # Auto 模式下增压值 (默认 +20mV)
}
```

### 6.4 测试模式对卡片的影响(`_on_test_mode_changed` → `_update_channel_cards_force_visibility`)

| 模式 | `force_mode_toggle` | `force_auto_stack` 容器 |
|---|---|---|
| `high_voltage` | 可见 | 可见(随 Force/Auto 切换显示 force_value 或 boost 控件) |
| `standard` | 隐藏 | 隐藏(卡片仅保留 Enable/Name/CH) |

新增卡片时(`_add_channel_config_card` 末尾)会调用一次 `_update_channel_cards_force_visibility`,确保新卡片遵循当前模式。

### 6.5 Force / Auto 切换逻辑

| 模式 | stack index | 可见控件 |
|---|---|---|
| `force` | 0 | `force_value_input` |
| `auto`  | 1 | `boost_mode_label` + `boost_mode_toggle` + `boost_value_input` |

切换由 `_on_force_mode_changed` 触发,调用 `force_auto_stack.setCurrentIndex(...)` 真正互斥显示。

### 6.6 信号连接

```python
enable_cb.toggled                 -> _on_config_enable_changed
name_combo.currentIndexChanged    -> _on_config_name_changed
channel_combo.currentIndexChanged -> _on_config_channel_changed
remove_btn.clicked                -> _remove_channel_config
force_mode_toggle.toggled         -> _on_force_mode_changed
force_value_input.textChanged     -> _on_force_value_changed
boost_mode_toggle.toggled         -> _on_boost_mode_changed
boost_value_input.textChanged     -> _on_boost_value_changed
```

---

## 七、Test Buttons Row

> 代码事实源: [view_panels.py `_create_test_buttons_row`](../../ui/pages/consumption_test/view_panels.py)

### 7.1 示意图

```
┌────────────────────────┐  ┌────────────────────────┐
│  ▶ START TEST          │  │  Auto Test             │
│  (绿色 #0d6b4f 底)     │  │  (深紫 #162544 底)      │
│  zap.svg 图标          │  │  activity.svg 图标     │
│  min-height 36px       │  │  min-height 36px       │
└────────────────────────┘  └────────────────────────┘
```

### 7.2 组件

| 组件 | 类型 | 说明 |
|---|---|---|
| `start_test_btn` | ProgressButton | 单次功耗测试;绿底 `#0d6b4f`,边框 `#18a87a` |
| `auto_test_btn` | ProgressButton | Auto Test 多 BIN 流程;深紫底 `#162544`,边框 `#25355c` |

两个按钮均 Expanding,各占 1 份;ProgressButton 提供 `clicked`(开始)与 `stop_clicked`(停止)双信号。

### 7.3 信号连接

```python
start_test_btn.clicked      -> _on_start_test
start_test_btn.stop_clicked -> _stop_test
auto_test_btn.clicked       -> _on_auto_test
auto_test_btn.stop_clicked  -> _stop_auto_test
```

---

## 八、Consumption Test Panel(结果展示)

> 代码事实源: [view_panels.py `_create_consumption_test_panel`](../../ui/pages/consumption_test/view_panels.py)

### 8.1 示意图

```
┌──────────────────────────────────────────────────────────────┐
│  ┌────────┐ ┌────────┐ ┌────────┐ ...                         │  ← result_cards_layout
│  │ Vbat   │ │ Vcore  │ │ VANA   │                             │     (QHBoxLayout,每通道一张)
│  │ - - -  │ │ - - -  │ │ - - -  │  ← value_label (电流值)     │
│  │ 3.8V   │ │ 1.1V   │ │ 1.8V   │  ← voltage_label (电压)     │
│  └────────┘ └────────┘ └────────┘                             │
├──────────────────────────────────────────────────────────────┤
│  BIN RESULTS                              [⤓ Export]          │  ← _bin_result_header(可隐藏)
├──────────────────────────────────────────────────────────────┤
│  BIN    │ Voltage       │ Vbat  │ Vcore │ ... │ Vbat_remain  │  ← bin_result_table
│  BIN-1  │ Vbat=3.8V,... │ 320uA │ 180uA │ ... │ 20uA         │     (QTableWidget,多 BIN 时显示)
│  BIN-2  │ ...           │ ...   │ ...   │ ... │ ...          │
├──────────────────────────────────────────────────────────────┤
│  [💾 Save DataLog]                                            │  ← save_datalog_btn
└──────────────────────────────────────────────────────────────┘
```

### 8.2 组件

| 组件 | 类型 | 说明 |
|---|---|---|
| `result_cards_container` | QWidget | 顶部通道结果卡片行 |
| `channel_cards[idx]` | dict | 每张卡片含 `value_label`/`voltage_label` 等 |
| `_vbat_remain_card` | dict \| None | Vbat_remain 卡片(有子通道时才显示) |
| `_bin_result_header` | QWidget | BIN 结果表标题 + Export 按钮 |
| `_bin_result_title` | QLabel | "BIN RESULTS",11px bold `#8eb0e3` |
| `export_bin_result_btn` | QPushButton | "⤓ Export",导出 xlsx |
| `bin_result_table` | QTableWidget | 多 BIN 对比表;列由 `_setup_bin_result_table` 动态生成 |
| `save_datalog_btn` | QPushButton | "Save DataLog",灰底 `#162544`,save.svg 16px |
| `_disabled_overlay` | QWidget | 未连接 N6705C 时的半透明遮罩,提示 "Please connect N6705C first" |

### 8.3 容器样式

| 项 | 值 |
|---|---|
| 容器 | `QFrame#consumptionPanel` |
| 背景 | `#0b1630`,边框 `1px solid #18284d`,圆角 12px |
| ContentsMargins | `(14, 10, 14, 10)` |
| 遮罩 | `rgba(5, 11, 26, 180)`,圆角 12px,`WA_TransparentForMouseEvents=False` |

### 8.4 BIN 表列生成规则(`_setup_bin_result_table`)

- 固定列:`BIN`, `Voltage`
- 启用通道列:每个 `enabled=True` 的通道一列(用其 `name`)
- 若存在非 Vbat 启用通道,追加 `Vbat_remain`
- 单 BIN 时整个表 + header 隐藏

### 8.5 信号连接

```python
export_bin_result_btn.clicked -> _on_export_bin_result   # 导出 Excel
save_datalog_btn.clicked      -> _on_save_datalog
```

---

## 九、ExecutionLogsFrame

> 由 `ExecutionLogsFrame.wrap_with(body, ...)` 包裹整个 body,形成 QSplitter(Qt.Vertical)。

| 项 | 值 |
|---|---|
| 分割器 | QSplitter(Qt.Vertical),隐式手柄 |
| stretch | `(1, 0)`(body 可拉伸,logs 固定) |
| sizes | `[600, 120]` |
| min_log_height | 40 |
| `log_edit` | QTextEdit(只读,日志输出) |
| `clear_log_btn` | QPushButton("Clear Log") |
| `append_log(msg)` | 主入口方法,所有 UI 日志均走此方法 |

---

## 十、Auto Test 测试逻辑

### 10.1 入口与触发链路

```
UI 点击 auto_test_btn (ProgressButton)
    ↓
_on_auto_test (consumption_test.py)
    收集参数: com_port / firmware_paths / download_mode / channel_configs /
              channel_force_configs / test_mode / config_text / 等
    ↓
ConsumptionController.start_auto_test(worker_kwargs)
    ↓
_AutoTestWorker.moveToThread(QThread) -> worker.run()
    ↓
_auto_test() 主流程
```

### 10.2 顶部常量(auto_test_worker.py)

```python
_CHIP_STABILIZATION_DELAY_SEC = 4.0    # 下载成功后稳定等待(秒)
_DOWNLOAD_PGM_RATE = 921600            # dldtool --pgm-rate 参数
```

### 10.3 主流程示意图(每 BIN 循环)

```
┌─────────────────────────────────────────────────────────────────────┐
│  入口预处理                                                          │
│  _prepare_channels_high_impedance()                                 │
│  → 对 Vbat + force_map 子通道 + POWERON + RESET                      │
│     统一 channel_off → set_mode("PS2Q") → set_output_off_mode("HIGHZ")│
└─────────────────────────────────────────────────────────────────────┘
                                ↓
        ┌────────────────────────────────────────────┐
        │  对每个 BIN 循环 (bin_idx, bin_path)         │
        └────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1-2: _prepare_poweron_vbat                                     │
│   • 配置 PowerON/RESET 通道 (PS2Q, 0.1V/2.3V 视极性)                 │
│   • Vbat 设 3.8V / 0.2A / PS2Q, 上电后等 0.5s                       │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3-6: _step_download_and_reset                                  │
│   Step 3: _start_download_async                                     │
│     → 后台线程跑 download_bin(com_port, bin_path, mode,             │
│                                pgm_rate=_DOWNLOAD_PGM_RATE,          │
│                                timeout=120)                          │
│     实际命令:                                                       │
│       dldtool.exe <port> --pgm-rate 921600                          │
│                  [ --ramrun ] <programmer.bin> [ <app.bin> ]         │
│                                                                      │
│   Step 4: 发 RESET → POWERON 脉冲,触发下载握手                       │
│     → _guard_download_handshake: 1s 后检查 dldtool 状态              │
│       卡在 preparing/waiting_sync 则重发 POWERON/RESET,最多 3 次    │
│                                                                      │
│   Step 5: download_thread.join(timeout=180)                          │
│     → dldtool stdout 解析 PROGRAMMING SUCCEEDED → SUCCEEDED          │
│                                                                      │
│   Step 6: 再发 POWERON + RESET 启动刚烧好的固件                       │
│     → _time.sleep(_CHIP_STABILIZATION_DELAY_SEC=4.0) 等稳定          │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 8b: _resolve_config_commands + _step_save_original_registers   │
│   (仅当 should_config=True 时执行,见 §10.4)                         │
│                                                                      │
│   • 解析配置(standard 模式按通道 Name 匹配 rail;否则回退 power_dist) │
│   • I2CInterface.initialize() + bes_chip_check()                     │
│   • 保存 original_registers(每个 WRITE/WRITE_BITS 目标寄存器原值)    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 8c(条件): _step_execute_config_commands                       │
│   仅当 standard 模式且 force_config_enabled=True 时,在 Vbat 测量前  │
│   先下发一次配置                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 7: _step_measure_vbat_total                                    │
│   • 子通道先全切 VMeter(避免 source 干扰主路)                       │
│   • vbat_inst.fetch_current_by_datalog([vbat_hw_ch],                 │
│                                       test_time, sample_period)      │
│   → 得到 vbat_current(Vbat 总电流)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 8: _step_record_default_voltages                               │
│   • 兜底再切 VMeter                                                  │
│   • 对每个子通道 measure_voltage(ch)                                 │
│   → default_voltages[(label, ch)] = DUT 当前电源轨电压               │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 9: _step_force_plus20(子通道切 PS2Q + 上电)                    │
│   每通道按 channel_force_configs 分支:                              │
│   ┌────────────────────────────────────────────────────┐            │
│   │ Force 模式(force_value 有效)                      │            │
│   │   → set_voltage(force_value)                       │            │
│   │   → 日志: Force -> {force_value}V (user override)  │            │
│   ├────────────────────────────────────────────────────┤            │
│   │ Auto 模式(默认)                                   │            │
│   │   constant: v_boosted = v_default + boost_value    │            │
│   │   percent:  v_boosted = v_default * (1 + boost)    │            │
│   │   → set_voltage(v_boosted)                         │            │
│   │   → 日志: {v_default}V -> {v_boosted}V (Auto +...) │            │
│   └────────────────────────────────────────────────────┘            │
│   • set_current_limit(ch, 1.0) → channel_on(ch)                     │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 10(条件): _step_execute_config_commands                       │
│   仅当 config_commands and i2c(即 standard 模式 should_config=True): │
│   • 通过 I2CInterface 下发 WRITE / WRITE_BITS / READ 命令            │
│   • 典型用途:关闭内部 LDO、切外供电路径                              │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 11(条件): _step_auto_set_voltages                             │
│   仅当 Step 10 跑了才执行(与 Step 10 联动)                          │
│   • Force 模式 → 保持 force_value                                    │
│   • Auto 模式 → aligned_v = _align_voltage(v_default)                │
│     (对齐到 50mV 网格或特殊电压 [0.625, 0.67, 0.725, 0.78])          │
│     new_v = max(aligned_v, v_default)                                │
│     → set_voltage(new_v)                                             │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 12: _step_sub_channel_consumption                              │
│   调用 common.py 同步并行采集:                                       │
│                                                                      │
│   build_datalog_tasks                                                │
│     → 每台 N6705C 一个 task,Vbat 作 monitor 通道时追加               │
│     → 采样周期 = sample_period × num_ch(默认 20us × N 通道)         │
│                                                                      │
│   configure_datalog_all                                              │
│     → 串行给每台设备 inst.configure_datalog(channels, test_time,     │
│                                            sample_period)            │
│                                                                      │
│   start_datalog_sync(threading.Barrier)                              │
│     → 所有设备同一时刻调 start_datalog,避免相位偏差                  │
│                                                                      │
│   wait_datalog_with_progress                                         │
│     → 等 test_time + 1s,0.5s 周期报进度                             │
│                                                                      │
│   fetch_datalog_all                                                  │
│     → 并发调 fetch_datalog_marker_results(channels, test_time)       │
│     → 返回 {ch: avg_current}                                         │
│                                                                      │
│   → results[(label, ch)] = avg_current                               │
│   → vbat_remain = 同设备 Vbat(monitor)的平均电流                    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 13: _step_restore_registers                                    │
│   若 Step 8b 保存了 original_registers,通过 I2C 写回原值             │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 14: _step_restore_vmeter                                       │
│   子通道调 restore_channels_to_vmeter(hw_channels)                   │
│   回 VMeter 模式,为下一个 BIN 准备干净状态                          │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 末尾: _collect_channel_voltages + _emit_summary                     │
│   • 收集各通道电压(Force 模式优先用 force_value)                     │
│   • 通过 build_summary_payload 输出三类日志行:                       │
│     [RESULT]  [bin_name] Vbat: ...uA | Vcore: ...uA | ...            │
│     [DATA]    [bin_name] <tab 分隔纯数值,顺序同上,贴 Excel>          │
│     [VOLTAGE] [bin_name] Vbat=3.8V, Vcore=1.1V, ...                  │
│                                                                      │
│   • 多 BIN 时 _emit_final_summary_table 输出对比表                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.4 should_config 判定(本次修改核心)

```
test_mode == "high_voltage":
    should_config = False
    → 跳过 8b/8c/10/11/13
    → 直接走 Step 9 的 Force Vol 参数逻辑
    → 日志: "High-voltage mode: skipping I2C config, using Force Vol parameters directly."

test_mode == "standard":
    only_vbat_channel = (force_map 为空)
    should_config = force_config_enabled or (not only_vbat_channel)
        注: standard 模式下 force_config_enabled 恒为 True(由 UI 传入)
    → 走 8b/8c/10/11/13 完整 I2C 配置流程
    → config_text 由 _build_config_text_for_standard_mode(enabled_configs) 生成:
        仅合并"启用通道 Name 匹配的 rail"配置
        (例:启用 Vcore 通道 → 只取 Vcore 文本框内容)
```

### 10.5 两种实际执行模式

| 模式 | 触发条件 | 实际行为 |
|---|---|---|
| **A. 外供高压模式** | `test_mode_toggle` = High V | 跳过 8b/8c/10/11/13;Step 9 用 Force Vol 参数;Channel Config 卡片显示 Force 控件 |
| **B. 标准电压模式** | `test_mode_toggle` = Std V | 8b 按 Channel Name 匹配 rail 配置 → 8c 前置下发 → Step 7 测 Vbat → Step 9 加压 → Step 10 I2C 配置 → Step 11 对齐 → Step 12 采集 → Step 13 还原;Channel Config 卡片隐藏 Force 控件 |

### 10.6 进度条分段(每 BIN 内部)

| 进度点 | 含义 |
|---|---|
| `base + 0.02 * span` | Step 1-2 PowerON/Vbat 配置 |
| `base + 0.04 * span` | Step 1-2 完成 |
| `base + 0.30 * span` | Step 3-5 下载完成 |
| `base + 0.35 * span` | Step 6 稳定等待完成 |
| `base + 0.50 * span` | Step 7 Vbat 测量完成 |
| `base + 0.55 * span` | Step 8 默认电压记录完成 |
| `base + 0.58 * span` | Step 9 子通道加压完成 |
| `base + 0.62 * span` | Step 10 I2C 配置下发完成 |
| `base + 0.65 * span` | Step 11 Auto Set 完成 |
| `base + 0.92 * span` | Step 12 datalog 采集完成 |
| `base + 1.0 * span`  | 当前 BIN 全部完成 |

### 10.7 每通道 force 配置契约

```python
channel_force_configs[(device_label, hw_ch)] = {
    "force_mode": "force" / "auto",        # 默认 "auto"
    "force_value": float | None,           # Force 模式下用户输入电压(V)
    "boost_mode":  "constant" / "percent", # Auto 模式默认 "constant"
    "boost_value": float,                  # Auto 模式默认 0.02
}
```

**分支逻辑**:
- `force_mode == "force"` 且 `force_value` 有效 → 直接用 `force_value` 作为该通道目标电压;
- `force_mode == "auto"` →
  - `boost_mode == "constant"` → `v_boosted = v_default + boost_value`
  - `boost_mode == "percent"`  → `v_boosted = v_default * (1 + boost_value)`

### 10.8 vbat_remain 含义

DUT 全部电源轨都被外供电接管后,Vbat 主路上剩余的"未被分通道贡献的"电流(典型对应 DUT 内部未接出来的电源轨)。

---

## 十一、配置快照(Import/Export Config)

> 代码事实源: [consumption_test.py `_collect_config_snapshot` / `_apply_imported_config`](../../ui/pages/consumption_test/consumption_test.py)

### 11.1 Schema

```json
{
  "schema_version": 2,
  "page": "consumption_test",
  "n6705c": {...},
  "serial_port": "...",
  "mcu_io": {...},
  "channel_configs": [...],
  "download": {...},
  "chip_selected": "bes2300p",
  "rail_configs": {
    "Vcore": "WRITE 0x100 0x1\n...",
    "VANA": "WRITE 0x200 0x2"
  },
  "test_mode": "high_voltage",
  "test": {
    "test_time": 10.0,
    "control_method": "N6705C",
    "poweron_channel": "B-CH1",
    "poweron_polarity": "rising",
    "reset_channel": "B-CH2",
    "reset_polarity": "rising",
    "reset_enabled": false
  }
}
```

### 11.2 版本兼容

- `schema_version = 2`:使用 `rail_configs` + `test_mode`(当前)
- `schema_version = 1`(旧版):使用 `config_text` + `force_config_enabled`
  - `_apply_imported_config` 检测到旧版 `config_text` 时,会全量填入所有非空 rail 文本框(向后兼容)

### 11.3 触发入口

- `import_config_btn.clicked` → `_import_config`(从 JSON 文件加载)
- `export_config_btn.clicked` → `_export_config`(导出到 JSON 文件)

---

## 十二、相关代码定位索引

| 关注点 | 文件 | 关键符号 |
|---|---|---|
| 页面整体布局 | `ui/pages/consumption_test/view_panels.py` | `_create_layout` |
| Header(标题 + Import/Export) | `ui/pages/consumption_test/view_panels.py` | `_create_layout` 顶部 |
| Config Import 面板 | `ui/pages/consumption_test/view_panels.py` | `_create_config_import_panel` |
| Connection Panel(N6705C A/B) | `ui/pages/consumption_test/view_panels.py` | `_create_connection_panel` |
| Firmware Download Panel | `ui/pages/consumption_test/view_panels.py` | `_create_firmware_panel` |
| Test Buttons Row | `ui/pages/consumption_test/view_panels.py` | `_create_test_buttons_row` |
| Consumption Test Panel(结果区) | `ui/pages/consumption_test/view_panels.py` | `_create_consumption_test_panel` / `_setup_bin_result_table` |
| Test Config Panel | `ui/pages/consumption_test/view_config.py` | `_create_test_config_panel` |
| Channel Config 区域 + 卡片 | `ui/pages/consumption_test/view_config.py` | `_create_channel_config_section` / `_add_channel_config_card` |
| 测试模式切换(Force 控件显隐) | `ui/pages/consumption_test/view_config.py` | `_on_test_mode_changed` / `_update_channel_cards_force_visibility` |
| Force/Auto 切换逻辑 | `ui/pages/consumption_test/view_config.py` | `_on_force_mode_changed` |
| Chip 选择 / rail YAML 加载 | `ui/pages/consumption_test/consumption_test.py` | `_on_chip_selected` / `_load_rail_configs_from_chip` |
| 每轨 Import / Exec | `ui/pages/consumption_test/consumption_test.py` | `_import_rail_configuration` / `_execute_rail_configuration` / `_update_chip_rail_yaml` |
| 配置快照 Import/Export | `ui/pages/consumption_test/consumption_test.py` | `_collect_config_snapshot` / `_apply_imported_config` |
| Auto Test UI 入口 | `ui/pages/consumption_test/consumption_test.py` | `_on_auto_test` |
| 标准电压模式 config_text 构建 | `ui/pages/consumption_test/consumption_test.py` | `_build_config_text_for_standard_mode` |
| 每通道 force 配置构建 | `ui/pages/consumption_test/consumption_test.py` | `_build_channel_force_configs` |
| AutoTestWorker 主流程 | `core/consumption_test/workers/auto_test_worker.py` | `_auto_test` |
| 测试模式判定(跳过 I2C) | `core/consumption_test/workers/auto_test_worker.py` | `_auto_test` 内 `should_config` 分支 |
| 下载命令构造 | `lib/download_tools/download_script.py` | `download_bin` |
| ForceHigh/ForceAuto worker | `core/consumption_test/workers/force_worker.py` | `BaseForceTestWorker` |
| datalog 同步采集 | `core/consumption_test/workers/common.py` | `build_datalog_tasks` 等 |
