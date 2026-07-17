# Consumption Test 汇总

> 本文件汇总当前 `consumption_test` 页面中 **Config Import** 区域的布局/组件,以及 **Auto Test** 完整测试逻辑,附带 ASCII 示意图便于直观理解。
>
> 代码事实源:
> - UI: [ui/pages/consumption_test/view_panels.py](../../ui/pages/consumption_test/view_panels.py)
> - UI: [ui/pages/consumption_test/view_config.py](../../ui/pages/consumption_test/view_config.py)
> - UI: [ui/pages/consumption_test/consumption_test.py](../../ui/pages/consumption_test/consumption_test.py)
> - Worker: [core/consumption_test/workers/auto_test_worker.py](../../core/consumption_test/workers/auto_test_worker.py)
> - Worker: [core/consumption_test/workers/force_worker.py](../../core/consumption_test/workers/force_worker.py)
> - Common: [core/consumption_test/workers/common.py](../../core/consumption_test/workers/common.py)

---

## 一、Config Import 区域布局与组件

### 1.1 区域整体示意图

```
┌─────────────────────────────────────────────────────────────┐
│  Config Import                                              │
│  ┌──┐ file-json.svg  Config Import      [ ] Force           │
│  │📄│  (icon 16x16)   (12px bold white)  (右上角 QCheckBox) │
│  └──┘                                                        │
├─────────────────────────────────────────────────────────────┤
│  Chip   [────────────── 选芯片 ──────────────] [ Check ]    │
│   ↑      ↑ DarkComboBox 22px                  ↑ 60x22 btn   │
│  QLabel  ↑ Expanding/Ignored 策略             ↑ 触发 I2C    │
│  10px    ↑ 首项 "-- Select Chip --"           ↑ chip check  │
│  #7e96bf ↑ 余项填 SUPPORTED_CHIPS                          │
├─────────────────────────────────────────────────────────────┤
│  Config [────────── 选 saved config ──────────]             │
│   ↑      ↑ DarkComboBox 22px (初始 disabled)               │
│  QLabel  ↑ 首项 "-- Select Config --"                      │
│  10px    ↑ tooltip → chips/.../main_chip_configs/<chip>.yaml│
│  宽度    ↑ 选择 chip 后才启用                               │
│  对齐    ↑                                                   │
│  Chip    ↑                                                   │
├─────────────────────────────────────────────────────────────┤
│  Config Content                                             │
│   ↑ QLabel 10px #7e96bf (纯标签)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Paste YAML config here...                              │ │
│  │                                                        │ │
│  │  QPlainTextEdit (60~120px 高)                          │ │
│  │  Consolas 10px                                         │ │
│  │  border #25355c, focus 紫 #5d45ff                      │ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [ 📤 Import ]              [ ⚙ Exec ]                      │
│   ↑ 灰底 #162544 30px        ↑ 紫底 #5d45ff 30px            │
│   ↑ upload.svg 图标          ↑ settings.svg 图标           │
│   ↑ 从 yaml/文本导入配置     ↑ 立即通过 I2C 下发一次        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 容器与布局参数

| 项 | 值 |
|---|---|
| 容器 | `QFrame#configPanel` |
| 背景 | `#0b1630` |
| 边框 | `1px solid #18284d` |
| 圆角 | `12px` |
| 内部 Layout | `QVBoxLayout` |
| ContentsMargins | `(12, 10, 12, 10)` |
| Spacing | `6` |

### 1.3 自上而下 6 行组件清单

#### Row 1 — 标题行 `config_title_row` (QHBoxLayout, spacing=4)

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `config_icon_label` | QLabel | 16×16,file-json.svg,tint `#94a3b8` |
| `config_title` | QLabel | "Config Import",12px bold,`#ffffff` |
| stretch | — | 右推 Force |
| `force_config_cb` | QCheckBox | "Force",11px `#dbe7ff`;控制是否强制下发 I2C 寄存器配置 |

**Force 复选框语义**:
- 未勾选(默认):仅当存在 Vbat 之外子通道时才查找/下发配置;只有 Vbat 时跳过。
- 勾选:不管通道数都配置,且在 Vbat 测试前额外先下发一次,让 DUT 测 Vbat 时已处于目标配置。

#### Row 2 — Chip 行 `chip_row` (QHBoxLayout, spacing=4)

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `chip_select_label` | QLabel | "Chip",10px,`#7e96bf` |
| `chip_combo` | DarkComboBox | 22px 高,Expanding/Ignored;首项 "-- Select Chip --",余项 `SUPPORTED_CHIPS` |
| `chip_check_btn` | QPushButton | "Check",60×22,11px,灰底 `#162544`,hover `#1c315b`;触发 I2C chip check |

#### Row 3 — Config 行 `saved_config_row` (QHBoxLayout, spacing=4)

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `saved_config_label` | QLabel | "Config",10px,宽度对齐 Chip 标签 |
| `saved_config_combo` | DarkComboBox | 22px 高,初始 disabled;首项 "-- Select Config --";tooltip → `chips/bes_chip_configs/main_chip_configs/<chip>.yaml` |

#### Row 4 — Config Content 标签

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `config_file_label` | QLabel | "Config Content",10px,`#7e96bf` |

#### Row 5 — Config Content 文本框

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `config_text_edit` | QPlainTextEdit | 60~120px 高;placeholder "Paste YAML config here...";Consolas 10px;border `#25355c`;focus 紫 `#5d45ff` |

#### Row 6 — 按钮行 `config_btn_row` (QHBoxLayout, spacing=4)

| 组件 | 类型 | 关键属性 |
|---|---|---|
| `import_config_btn` | QPushButton | "Import",灰底 `#162544`,upload.svg 图标,30px 高,11px;从 yaml/文本导入配置 |
| `execute_config_btn` | QPushButton | "Exec",紫底 `#5d45ff`,settings.svg 图标,30px 高,11px;立即通过 I2C 下发一次配置 |

### 1.4 信号连接

```python
chip_combo.currentIndexChanged        -> _on_chip_selected
chip_check_btn.clicked                -> _on_chip_check
import_config_btn.clicked             -> _import_configuration
execute_config_btn.clicked            -> _execute_configuration
saved_config_combo.currentIndexChanged -> _on_saved_config_selected
```

### 1.5 配置解析优先级(AutoTest 中 `_resolve_config_commands`)

```
1. config_text(文本框内容)非空
   → 直接用 parse_config_commands_fn 解析文本框 YAML
   → 忽略 saved_config_combo 和 chip config

2. 否则用 chip_config.power_distribution 字典
   → 拼接 raw_lines 后再解析
```

---

## 二、Channel Config 卡片(配套组件)

> 代码事实源: [view_config.py L436-L790](../../ui/pages/consumption_test/view_config.py)

### 2.1 卡片整体示意图

```
┌───────────────────────────────────┐
│  [x] Enable                [✕]    │  ← top_row: Enable + remove_btn
├───────────────────────────────────┤
│  Name  [──────── Vbat ────────▼]  │  ← name_row: QLabel(32px) + DarkComboBox
├───────────────────────────────────┤
│  CH    [──────── A-CH1 ───────▼]  │  ← ch_row: QLabel(32px) + DarkComboBox
├───────────────────────────────────┤
│  [  Force  │  Auto  ]              │  ← force_mode_toggle: BinaryTextToggle
│        (当前:Auto)                 │     (140px 宽,22px 高)
├───────────────────────────────────┤
│  ┌──── Force 模式可见(Page 0)──┐  │  ← force_auto_stack: QStackedLayout
│  │                              │  │
│  │  [──────── V (Force) ──────] │  │     - force_value_input (QLineEdit)
│  │                              │  │
│  └──────────────────────────────┘  │
│  ┌──── Auto 模式可见(Page 1)───┐  │
│  │                              │  │
│  │  Boost Mode                  │  │     - boost_mode_label (QLabel)
│  │  [  Const  │   Pct  ]        │  │     - boost_mode_toggle (BinaryTextToggle)
│  │                              │  │     - boost_value_input (QLineEdit)
│  │  [────── boost value ──────] │  │
│  │                              │  │
│  └──────────────────────────────┘  │
└───────────────────────────────────┘

卡片: 宽 160px (fixed), 最小高 220px
内部 QVBoxLayout: margins=(10,8,10,8), spacing=5
```

### 2.2 卡片每通道数据契约

```python
{
  "name": "Vbat",
  "channel": "A-CH1",
  "enabled": True,
  "force_mode": "auto",          # "force" / "auto"  (默认 "auto")
  "force_value": "",             # Force 模式下用户输入电压(V)
  "boost_mode": "constant",      # "constant" / "percent"  (Auto 模式默认)
  "boost_value": "0.02",         # Auto 模式下增压值 (默认 +20mV)
}
```

### 2.3 Force / Auto 切换逻辑

| 模式 | 显示页(stack index) | 可见控件 |
|---|---|---|
| `force` | 0 | `force_value_input` |
| `auto`  | 1 | `boost_mode_label` + `boost_mode_toggle` + `boost_value_input` |

切换由 `_on_force_mode_changed` 触发,调用 `force_auto_stack.setCurrentIndex(...)` 实现真正的"互斥显示"(不是 enable/disable)。

---

## 三、Auto Test 测试逻辑

### 3.1 入口与触发链路

```
UI 点击 auto_test_btn (ProgressButton)
    ↓
_on_auto_test (consumption_test.py L2117)
    收集参数:com_port / firmware_paths / download_mode / channel_configs /
              channel_force_configs / force_config_enabled / 等
    ↓
ConsumptionController.start_auto_test(worker_kwargs)
    ↓
_AutoTestWorker.moveToThread(QThread) -> worker.run()
    ↓
_auto_test() 主流程
```

### 3.2 顶部常量(auto_test_worker.py)

```python
_CHIP_STABILIZATION_DELAY_SEC = 4.0    # 下载成功后稳定等待(秒)
_DOWNLOAD_PGM_RATE = 921600            # dldtool --pgm-rate 参数
```

### 3.3 主流程示意图(每 BIN 循环)

```
┌─────────────────────────────────────────────────────────────────────┐
│  入口预处理                                                          │
│  _prepare_channels_high_impedance()                                 │
│  → 对 Vbat + force_map 子通道 + POWERON + RESET                      │
│     统一执行 channel_off → set_mode("PS2Q") → set_output_off_mode("HIGHZ") │
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
│   (仅当 should_config=True 时执行)                                   │
│                                                                      │
│   should_config = force_config_enabled or (存在 Vbat 之外的子通道)   │
│                                                                      │
│   • 解析配置(优先文本框 > chip_config.power_distribution)            │
│   • I2CInterface.initialize() + bes_chip_check()                     │
│   • 保存 original_registers(每个 WRITE/WRITE_BITS 目标寄存器原值)    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 8c(条件): _step_execute_config_commands                       │
│   仅当 force_config_enabled=True 时,在 Vbat 测量前先下发一次配置     │
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
│   仅当 config_commands and i2c:                                      │
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

### 3.4 三种实际执行模式

| 模式 | 触发条件 | 实际行为 |
|---|---|---|
| **A. 纯 Vbat 测试** | 只 enable Vbat + Force 未勾选 | 跳过 8b/8c/10/11;只有 Step 7 测 Vbat 总电流(无子通道加压) |
| **B. 默认配置+加压** | Vbat + 子通道 + Force 未勾选 | 8b 保存寄存器 → Step 7 测 Vbat → Step 9 加压 → Step 10 I2C 配置 → Step 11 对齐 → Step 12 采集 |
| **C. 强制配置+加压** | 任意通道 + **Force 勾选** | 比 B 多:Step 7 前先下发一次配置;即使只有 Vbat 也走完整配置流程 |

### 3.5 should_config 判定流程

```
                   enable 通道数?
                        │
        ┌───────────────┴───────────────┐
        │                               │
    只有 Vbat                        有子通道
        │                               │
   Force 勾选?                     Force 勾选?
        │                               │
   ┌────┴────┐                     ┌────┴────┐
   是        否                    是        否
   │         │                     │         │
   ▼         ▼                     ▼         ▼
  模式 C   模式 A                 模式 C   模式 B
  (强制     (纯 Vbat               (强制     (默认
   配置,    测试,                  配置,     配置+
   无子     无配置                 +加压)    加压)
   通道     无加压)
   加压)
```

### 3.6 进度条分段(每 BIN 内部)

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

### 3.7 每通道 force 配置契约

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

### 3.8 vbat_remain 含义

DUT 全部电源轨都被外供电接管后,Vbat 主路上剩余的"未被分通道贡献的"电流(典型对应 DUT 内部未接出来的电源轨)。

---

## 四、相关代码定位索引

| 关注点 | 文件 | 关键行 |
|---|---|---|
| Config Import 面板构建 | `ui/pages/consumption_test/view_panels.py` | L328-L549 |
| Channel Config 卡片构建 | `ui/pages/consumption_test/view_config.py` | L436-L790 |
| Force/Auto 切换逻辑 | `ui/pages/consumption_test/view_config.py` | `_on_force_mode_changed` |
| Auto Test UI 入口 | `ui/pages/consumption_test/consumption_test.py` | `_on_auto_test` L2117 |
| 每通道 force 配置构建 | `ui/pages/consumption_test/consumption_test.py` | `_build_channel_force_configs` L1240 |
| AutoTestWorker 主流程 | `core/consumption_test/workers/auto_test_worker.py` | `_auto_test` L272 |
| 下载命令构造 | `lib/download_tools/download_script.py` | `download_bin` L656 |
| ForceHigh/ForceAuto worker | `core/consumption_test/workers/force_worker.py` | L45-L345 |
| datalog 同步采集 | `core/consumption_test/workers/common.py` | L46-L162 |
