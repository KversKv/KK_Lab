# KK'1811 PMU 配置工具

图形化配置 1811 PMIC：通过 USB 转 I2C（设备地址 0x17，10 位寄存器地址，16 位数据）控制各 LDO / BUCK 的使能、模式与输出电压。

本包按 **UI层 / 算法层 / 驱动中间层** 分离，取代早期单文件实现。

<br />

1811 寄存器地址和描述见ui\pages\pmu\pmu\_1811\data\1811 pmu inf reg.csv\
1811 LDO输出电压见ui\pages\pmu\pmu\_1811\data\BES1811 LDO输出电压范围.csv

***

## 1. 目录结构

```
ui/pages/pmu/pmu_1811/
├── __init__.py              # 公共 API: 导出 Pmu1811UI
├── constants.py             # 配色 / 字体 / 画布几何常量
├── models.py                # 【算法层】PmuModule / LayoutRow / 拓扑布局 / 默认状态工厂
├── workers.py               # 【驱动中间层】I2C 异步 Worker (QThread)
├── page.py                  # 【UI层入口】Pmu1811UI 主页面
└── widgets/                 # 【UI层】可复用控件
    ├── __init__.py
    ├── toggle_switch.py     # iOS 风格拨动开关
    ├── module_card.py       # 模块卡片 (LED + 名称 + 电压步进 + 齿轮; 仅 LDO/BUCK)
    ├── switch_widget.py     # SW 物理开关模型 (左右端点 + 动态连杆, 单击切换闭合/开路)
    ├── diagram_canvas.py    # 拓扑画布 (VSYS / 子母线 / 树状分支连线)
    ├── property_panel.py    # 属性面板 (使能/模式/电压/I2C/连接信息; SW 专属 Switch Controls)
    └── context_menu.py      # 右键菜单 (使能切换 + 模式选择)
```

***

## 2. 分层职责

| 层         | 文件                     | 职责                                                                               | 依赖方向                      |
| --------- | ---------------------- | -------------------------------------------------------------------------------- | ------------------------- |
| **算法层**   | `models.py`            | 领域数据模型 + 拓扑布局 + 默认模块状态工厂（从 `chips/bes1811_pmu.py` 芯片寄存器表构建）                      | ← 依赖 `chips/`             |
| **驱动中间层** | `workers.py`           | QThread Worker，桥接 UI 与 `core/bes1811_pmu_controller.py`；每次操作自建/销毁 I2C 接口，避免跨线程共享 | ← 依赖 `core/`              |
| **UI层**   | `page.py` + `widgets/` | 纯 Qt 控件与页面编排，不直接访问硬件                                                             | ← 依赖 `models` / `workers` |

依赖铁律（与项目分层一致 `main→ui↔core→instruments→lib`）：

- UI 层禁止阻塞 IO，必须通过 `workers.py` 走 QThread
- `workers.py` 不持有 Qt Widget 引用，只发射 Signal
- `models.py` 不依赖 Qt

***

## 3. 核心数据模型

### 3.1 `PmuModule`（`models.py`）

单个 LDO / BUCK / SW 模块的运行时状态：

| 字段                | 类型    | 说明                                      |
| ----------------- | ----- | --------------------------------------- |
| `id`              | str   | 模块标识，如 `LDO_01` / `BUCK_03` / `SW1`    |
| `type`            | str   | `"LDO"` / `"BUCK"` / `"SW"`             |
| `enabled`         | bool  | 使能状态（SW: True=闭合 / False=开路）            |
| `mode`            | str   | `Normal` / `LP`（BUCK 还支持 `ULP`；SW 无模式）  |
| `voltage`         | float | 当前电压（V）（SW 不使用）                         |
| `min/max_voltage` | float | 电压范围（来自芯片表，已对齐 step）（SW 不使用）            |
| `step`            | float | 步进（来自 `chips/bes1811_pmu.get_ldo_step`） |
| `input`           | str   | 输入源（`VSYS` / `BUCK_01` / `vdd_l5` / `LDO_01&BUCK_01` 等） |
| `controllable`    | bool  | 是否支持 I2C 寄存器控制                          |
| `rdson`           | float | SW 专用：导通电阻 Rdson（mΩ）                    |
| `output`          | str   | SW 专用：输出节点（负载侧）                         |

属性：

- `modes` — 返回该类型支持的模式列表（SW 返回 `[]`）
- `reg_map` — 从 `chips/bes1811_pmu.get_reg_map` 取回寄存器映射（`pu` / `vbit_normal` / `pu_status` 字段）；SW 返回 None
- `sw_reg_map` — SW 专用：从 `chips.bes1811_pmu.get_sw_reg_map` 取回 `SwRegMap`（`en` / `en_dr`）；非 SW 返回 None

### 3.2 `LayoutRow`（`models.py`）

画布布局行，描述一行是模块还是子母线：

```python
LayoutRow(kind="module", id="LDO_01", level=1, input="VSYS")
LayoutRow(kind="bus",    id="vdd_l5", level=1, input="VSYS", bus_name="vdd_l5")
# 并联对偶 (输出短接, 互斥使能)
LayoutRow(kind="module", id="LDO_01", level=1, input="VSYS",
          pair="BUCK_01", pair_layout="vertical")
```

- `level=1` → 直连 VSYS，画在画布左列（`CARD_X_L1`）
- `level=2` → 二级支路，画在右列（`CARD_X_L2`），由子母线（蓝色）级联
- `pair` → 并联对偶伙伴 ID（BUCK↔LDO 输出短接）；`pair_layout="vertical"` →
  相邻行上下放置，两卡片同列（`CARD_X_L1`），各自从 VSYS 取电，输出端（卡片右边）
  用紫色竖线短接，表示两路并联到同一轨

### 3.3 `_LAYOUT_ROWS`

22 个模块 + 2 条子母线（`vdd_l14_15` / `vdd_l5`）+ 7 个 SW（Power Switch）。
其中 4 组并联对偶（输出短接、互斥使能）：
`BUCK_01↔LDO_01` / `BUCK_02↔LDO_02` / `BUCK_03↔LDO_03` / `BUCK_06↔LDO_06`。
对偶表见 `models._PAIRS`，查询用 `get_pair_partner(id)`。
前 3 组为同列垂直对偶（`pair_layout="vertical"`，均 `CARD_X_L1`）；
`BUCK_06↔LDO_06` 为**跨列对偶**：`BUCK_06`（L1, `VSYS`）置于 `CARD_X_L1`，
`LDO_06`（L2, 由 `LDO_02&BUCK_02` 供电）置于 `CARD_X_L2` 且在 `BUCK_06` 上方，
`BUCK_06` 输出横跨第二列后与 `LDO_06` 输出紫色短接（`_draw_pairs` 取两卡片右边
最大值 +14 作为短接竖线 x，支持跨列）。
`LDO_12` VIN 取自 `BUCK_02`（即 `LDO_02&BUCK_02` 对偶输出轨，由 `_draw_vin_tree` 渲染）；
`LDO_13` VIN 直连 `VSYS`（level 1），作为 SW5/SW6 单模块源。

SW（SW1~SW7）按 VIN 源级别分列：源为 L1（对偶如 `LDO_01&BUCK_01`，或单模块如 `LDO_13`）→ SW 是 L2，置于 `CARD_X_L2`；
源为 L2 单模块 → SW 是 L3，置于 `CARD_X_L3`。`input` 非 `VSYS`。
画布连线统一由 `_draw_wire_tree` 树状渲染（源点 → 水平干线 → 竖直干线 → 各分支，
竖直干线覆盖源与所有分支的 min/max 范围，无悬空端点），分两类调用：
- **对偶源**（input 含 `&`）：`_draw_vin_tree`，从对偶短接点引一条蓝色干线
  （`SUB_BUS_X`），L2 + SW + L1 对偶成员（如 `LDO_06`）共享干线，各分支段用类型色
  （L2 蓝 / SW 玫红 / L1 对偶成员蓝）。
- **单模块源**（如 `LDO_13`）：`_draw_sw_connections`，从源卡片右边
  （L1→`CARD_X_L1+CARD_W` / L2→`CARD_X_L2+CARD_W`）经干线
  （L1 源→`SUB_BUS_X` / L2 源→`SW_BUS_X`）引至 SW 开关模型左缘
  （L1 源→`CARD_X_L2` / L2 源→`CARD_X_L3`）。
- 母线 / 级联子树（`_draw_subtree`）同样走 `_draw_wire_tree`（蓝色干线）。
SW 不使用卡片，由 `SwitchWidget` 绘制拟物化开关符号：输入引线（左缘→左端子，玫红，
与行中心对齐使上游连线零偏移衔接）、左右玫红端点、动态连杆（闭合=绿色水平 /
开路=灰色上倾 28°）、输出短截线与 CLOSED/OPEN 状态文本；单击模型即切换闭合/开路，
属性面板对应显示专属 "Switch Controls" 区（开关 + 状态）与 "Physical Parameters"
（Rdson / Input / Output）。
SW 元数据见 `models._SW_DEFS`，寄存器映射见 `chips.bes1811_pmu.SW_REG_MAPS`。

### 3.4 `_default_modules()`

从芯片寄存器表构建初始模块字典：

1. 调用 `is_ldo_controllable(id)` 判断是否支持 I2C
2. 通过 `get_voltage_range(id)` 取真实电压范围
3. 通过 `get_ldo_step(id)` 取 step，并用 `snap_range_to_step` 对齐 min/max
4. 默认电压：BUCK=1.0V，LDO=范围中点偏下并 `align_to_step`

### 3.5 模块连接关系与位置表（`_LAYOUT_ROWS` 速查）

下表为 `_LAYOUT_ROWS` 全部 22 模块 + 2 子母线的连接关系与画布位置索引。
**行序** = `_LAYOUT_ROWS` 中的下标（决定画布从上到下的 Y 顺序）；
**卡片列** = `_card_x()` 推导出的 x 列（L1=`CARD_X_L1` / L2=`CARD_X_L2` / L3=`CARD_X_L3`）；
**VIN 输入** = 模块取电来源；**pair** = 输出短接的对偶伙伴（`_draw_pairs` 紫色短接）。

| 行序 | 模块 / 母线 ID    | 类型 | level | VIN 输入           | 卡片列 | pair    | 备注                                    |
| ---- | --------------- | ---- | ----- | ------------------ | ------ | ------- | --------------------------------------- |
| 0    | BUCK_01         | BUCK | 1     | VSYS               | L1     | LDO_01  | 对偶组 1 (`pair_layout=vertical`)        |
| 1    | LDO_01          | LDO  | 1     | VSYS               | L1     | BUCK_01 | 同列垂直, 输出紫色短接                    |
| 2    | SW1             | SW   | 1     | LDO_01&BUCK_01     | L2     | —       | VIN 源为 L1 对偶 → SW 是 L2              |
| 3    | SW7             | SW   | 1     | LDO_01&BUCK_01     | L2     | —       | 同上                                    |
| 4    | BUCK_02         | BUCK | 1     | VSYS               | L1     | LDO_02  | 对偶组 2                                 |
| 5    | LDO_02          | LDO  | 1     | VSYS               | L1     | BUCK_02 | 同列垂直                                 |
| 6    | LDO_12          | LDO  | 2     | BUCK_02            | L2     | —       | 取对偶轨半 id, `_draw_vin_tree` 渲染      |
| 7    | SW2             | SW   | 1     | LDO_02&BUCK_02     | L2     | —       | VIN 源为 L1 对偶                          |
| 8    | LDO_06          | LDO  | 2     | LDO_02&BUCK_02     | L2     | BUCK_06 | **跨列对偶**, 由对偶轨整体供电            |
| 9    | BUCK_06         | BUCK | 1     | VSYS               | L1     | LDO_06  | 输出横跨第二列与 LDO_06 紫色短接          |
| 10   | BUCK_03         | BUCK | 1     | VSYS               | L1     | LDO_03  | 对偶组 3                                 |
| 11   | LDO_03          | LDO  | 1     | VSYS               | L1     | BUCK_03 | 同列垂直                                 |
| 12   | LDO_07          | LDO  | 2     | BUCK_03            | L2     | —       | 级联子树 (`_draw_subtree`)               |
| 13   | LDO_08          | LDO  | 2     | BUCK_03            | L2     | —       | 同上                                    |
| 14   | LDO_09          | LDO  | 2     | BUCK_03            | L2     | —       | 同上                                    |
| 15   | LDO_10          | LDO  | 2     | BUCK_03            | L2     | —       | 同上                                    |
| 16   | LDO_11          | LDO  | 2     | BUCK_03            | L2     | —       | 同上                                    |
| 17   | SW3             | SW   | 1     | LDO_03&BUCK_03     | L2     | —       | VIN 源为 L1 对偶                          |
| 18   | SW4             | SW   | 1     | LDO_03&BUCK_03     | L2     | —       | 同上                                    |
| 19   | BUCK_04         | BUCK | 1     | VSYS               | L1     | —       | 独立 BUCK                                |
| 20   | BUCK_05         | BUCK | 1     | VSYS               | L1     | —       | 独立 BUCK                                |
| 21   | vdd_l14_15      | bus  | 1     | VSYS               | —      | —       | 子母线药丸 (`_draw_subtree`)             |
| 22   | LDO_14          | LDO  | 2     | vdd_l14_15         | L2     | —       | 挂 vdd_l14_15 母线                       |
| 23   | LDO_15          | LDO  | 2     | vdd_l14_15         | L2     | —       | 同上                                    |
| 24   | LDO_VMIC1       | LDO  | 2     | vdd_l14_15         | L2     | —       | 同上                                    |
| 25   | LDO_VMIC2       | LDO  | 2     | vdd_l14_15         | L2     | —       | 同上                                    |
| 26   | vdd_l5          | bus  | 1     | VSYS               | —      | —       | 子母线药丸                                |
| 27   | LDO_05          | LDO  | 2     | vdd_l5             | L2     | —       | 挂 vdd_l5 母线                           |
| 28   | LDO_13          | LDO  | 1     | VSYS               | L1     | —       | 作为 SW5/SW6 单模块源                    |
| 29   | SW5             | SW   | 1     | LDO_13             | L2     | —       | VIN 源为 L1 单模块 → SW 是 L2            |
| 30   | SW6             | SW   | 1     | LDO_13             | L2     | —       | 同上                                    |

**VIN 树归属**（`_draw_vin_tree` / `_draw_sw_connections`）：

| VIN 源                | 子模块 (从该源取电)                | 渲染函数             | 干线 x     |
| --------------------- | ----------------------------- | ------------------- | ---------- |
| VSYS                  | 所有 level=1 模块 + bus        | VSYS 横线 (琥珀)    | `VSYS_X`   |
| `LDO_01&BUCK_01`      | SW1, SW7                      | `_draw_vin_tree`    | `SUB_BUS_X` |
| `LDO_02&BUCK_02`      | LDO_12, SW2, LDO_06           | `_draw_vin_tree`    | `SUB_BUS_X` |
| `LDO_03&BUCK_03`      | LDO_07~11, SW3, SW4           | `_draw_vin_tree`    | `SUB_BUS_X` |
| `BUCK_03` (单模块源)   | LDO_07~11 (input 取半 id)      | `_draw_vin_tree` 内 | `SUB_BUS_X` |
| `vdd_l14_15` (bus)    | LDO_14, LDO_15, LDO_VMIC1/2   | `_draw_subtree`     | `SUB_BUS_X` |
| `vdd_l5` (bus)        | LDO_05                        | `_draw_subtree`     | `SUB_BUS_X` |
| `LDO_13` (单模块源)    | SW5, SW6                      | `_draw_sw_connections` | `SUB_BUS_X` (L1 源) |

**对偶组**（`_PAIRS`，输出紫色短接）：

| 对偶组            | 输入差异                          | 布局                |
| ----------------- | --------------------------------- | ------------------- |
| BUCK_01 ↔ LDO_01  | 均 VSYS                           | 同列垂直 (L1)       |
| BUCK_02 ↔ LDO_02  | 均 VSYS                           | 同列垂直 (L1)       |
| BUCK_03 ↔ LDO_03  | 均 VSYS                           | 同列垂直 (L1)       |
| BUCK_06 ↔ LDO_06  | BUCK_06=VSYS, LDO_06=LDO_02&BUCK_02 | **跨列** (BUCK_06@L1, LDO_06@L2) |

***

## 4. 工作逻辑

### 4.1 启动流程

```
Pmu1811UI.__init__
  ├─ _default_modules()              # 从芯片表构建 22 个模块
  ├─ _build_header()                # 顶部标题栏 + Check 按钮
  ├─ _build_chip_config()           # 顶部 Chip Config 区 (Auto/Force Normal/Force RC/Force Sleep, 功能留空)
  ├─ DiagramCanvas(modules)         # 渲染拓扑画布
  ├─ PropertyPanel                  # 右侧属性面板（默认隐藏）
  ├─ ExecutionLogsFrame.wrap_with   # 底部日志（QSplitter）
  └─ 信号连接 (canvas ↔ panel ↔ menu)
```

### 4.2 首次显示自动 Check

`showEvent` 触发 `QTimer.singleShot(0, self._on_check)`，等 UI 完全布局后：

1. 创建 `LdoReadAllWorker` 并 moveToThread
2. Worker 内部 `Bes1811PmuController.connect()` → `read_all_ldos()`
3. `finished` 信号回到主线程 → `_on_read_all_done` 把状态写回 `_modules`
4. 刷新所有卡片 + 当前选中模块的属性面板

### 4.3 用户操作数据流

所有用户输入经 UI → 本地状态更新 → 异步下发 I2C：

```
┌─────────────┐    Signal      ┌────────────┐   QThread    ┌──────────────────┐
│  UI 控件    │ ────────────▶ │  page.py   │ ───────────▶ │  Worker (workers)│
│ (card/panel)│                │ _on_xxx    │              │  → ctrl.set_*    │
└─────────────┘                │ _start_write│              │  → finished/error│
                                └────────────┘              └────────┬─────────┘
                                       ▲                              │
                                       │  Signal (主线程)              ▼
                                       └────────── _on_write_done ◀──┘
```

**三种写入动作**（`LdoWriteWorker.action`）：

- `"enable"` → `ctrl.set_ldo_enabled(id, bool)`
- `"mode"` → `ctrl.set_ldo_mode(id, str)`
- `"voltage"` → `ctrl.set_ldo_voltage(id, float)`

### 4.4 关键交互路径

| 触发源            | 信号                            | page.py 处理                      | 是否写 DUT                   |
| -------------- | ----------------------------- | ------------------------------- | ------------------------- |
| 卡片单击           | `canvas.module_selected`      | `_on_select`                    | 否                         |
| SW 开关模型单击      | `canvas.enable_toggled`       | `_on_card_enable`               | **是** (`enable`)          |
| 卡片右键           | `canvas.module_right_clicked` | `_on_context` → 弹 `ContextMenu` | 否                         |
| 卡片 +/−         | `canvas.voltage_stepped`      | `_on_card_voltage`              | **是** (`voltage`)         |
| 面板开关           | `panel.enable_changed`        | `_on_panel_enable`              | **是** (`enable`，对偶模块触发互锁) |
| 面板模式           | `panel.mode_changed`          | `_on_panel_mode`                | **是** (`mode`)            |
| 面板 Spin/Slider | `panel.voltage_changed`       | `_on_panel_voltage`             | **是** (`voltage`)         |
| 右键菜单开关         | `menu.enable_toggled`         | `_on_menu_enable`               | **是** (`enable`，对偶模块触发互锁) |
| 右键菜单模式         | `menu.mode_changed`           | `_on_menu_mode`                 | **是** (`mode`)            |
| Check 按钮       | clicked                       | `_on_check`                     | **是**（读全量）                |
| Chip Config 按钮 | `chipCfgBtn.clicked`          | `_on_chip_config`               | 否（功能留空，仅记 WARN 日志）        |

### 4.5 写入保护

`_start_write` 内部依次检查：

1. `mod.controllable == False` → 直接返回（无寄存器映射）
2. `_i2c_connected == False` → 仅本地更新，debug 日志
3. `_worker_thread is not None` → 上次操作未完成，丢弃并 WARN

Worker 完成后 `_cleanup_worker` 调用 `thread.quit() + wait()`，重置状态并恢复 Check 按钮。

### 4.6 并联对偶使能互锁

`BUCK_01↔LDO_01` / `BUCK_02↔LDO_02` / `BUCK_03↔LDO_03` / `BUCK_06↔LDO_06` 四组
输出短接（同一轨冗余），不可同时驱动。使能走 `_start_enable_write`：

- **开启**某模块且存在对偶 → 走 `PairWriteWorker`，**一次 I2C 会话**内先开自己、再关对偶
  （`_start_pair_write` → `_on_pair_write_done` → `_apply_local_disable` 同步本地状态）
- **关闭**某模块 → 走普通 `LdoWriteWorker`，不影响对偶（用户可自由关闭）
- 未连接时仅本地更新（`_apply_local_disable` 关闭对偶 UI 状态）

***

## 5. I2C 驱动中间层

### 5.1 `workers.py` 四个 Worker

| Worker             | 信号                                             | 用途                    |
| ------------------ | ---------------------------------------------- | --------------------- |
| `LdoReadAllWorker` | `finished(dict)` / `error(str)` / `log(str)`   | 读取全部 LDO/BUCK/SW 状态    |
| `LdoReadOneWorker` | `finished(LdoState)` / `error` / `log`         | 读取单个模块（LDO/BUCK/SW）   |
| `LdoWriteWorker`   | `finished(ldo_id)` / `error` / `log`           | 写入使能/模式/电压（SW 仅使能）    |
| `PairWriteWorker`  | `finished(primary, partner)` / `error` / `log` | 并联对偶互锁写入（一次会话开自己+关对偶） |

### 5.2 关键约定（与 `core/bes1811_pmu_controller.py` 对齐）

- **每次操作自建/销毁控制器**：不持有持久 I2C 连接，避免跨线程共享问题
- **日志回调**：`_make_log_cb()` 把 controller 的 `(level, msg)` 包成 `"[LEVEL] msg"` 字符串发射 `log` 信号，主线程接到后直接 `execution_logs.append_log`
- **错误路径**：`connect()` 失败 → `error.emit("I2C 接口初始化失败")`；异常 → `logger.error(..., exc_info=True)` + `error.emit(str(e))`
- **`finally`** **保证释放**：无论成功失败都 `ctrl.disconnect()`

### 5.3 连接参数

通过 `_dll_path` / `_speed_mode` 注入（当前 `page.py` 默认 `None` → 使用 controller 默认 DLL 与 100K 速率）。

***

## 操作规则集合（业务级）

LDO / DCDC / BUCK / SW 等各类模块的使能状态判断、打开/关闭、模式切换、电压设置等实际硬件操作语义已单独整理至：

👉 [RULES.md](./RULES.md)

涵盖内容（按模块组织，后续可扩展）：

- **LDO** — 寄存器模型（9 个关键位域 `pu` / `pu_dr` / `pu_status` / `lp` / `lp_dr` / `vbit_*` / `res_sel_dr`）
  - 使能状态判断（依据 `dig_ldo_XX_pu` 状态位而非配置位 `pu`）
  - 打开/关闭 LDO 的两步写入流程
  - 模式切换、电压设置、读取流程、控制位/状态位语义对照
  - BUCK 与 LDO 的差异
- **DCDC** — 规划中
- **BUCK** — 寄存器模型（11 个位域, 无 `lp` / `lp_dr`, 有 `res_sel_dr` + 4 个 `bg_en` / `sw_en` 系列）+ 使能 + 电压已补全（5 步 bg\_en/sw\_en 调压序列）; 模式切换待补全
- **SW** — 寄存器模型（2 个位域 `en` / `en_dr`, 无独立状态位, 无模式/电压）; 强制闭合/开路 (`en_dr→en` 二步); 四种 (en_dr, en) 组合语义

***

## 6. 画布拓扑绘制

### 6.1 几何常量（`constants.py`）

| 常量                                         | 含义             |
| ------------------------------------------ | -------------- |
| `VSYS_X`                                   | VSYS 主母线 x 坐标  |
| `CARD_X_L1` / `CARD_X_L2`                  | 一级 / 二级卡片 x 坐标 |
| `SUB_BUS_X`                                | 子母线竖线 x 坐标     |
| `CARD_W` / `CARD_H` / `ROW_H` / `TOP_PAD`  | 卡片与行距          |
| `BUS_PILL_W` / `BUS_PILL_H` / `BUS_PILL_X` | 子母线药丸尺寸与位置     |

### 6.2 绘制层次（`DiagramCanvas.paintEvent`）

1. **VSYS 主母线**（琥珀色实线）— 跨所有 VSYS/bus 行
2. **一级 → VSYS 横线**（琥珀色半透明）— 每行一条（对偶两卡片各自从 VSYS 取电）
3. **子母线**（蓝色半透明，`_draw_subtree`）：
   - `vdd_l14_15` → LDO\_14/15/VMIC1/VMIC2
   - `vdd_l5` → LDO\_05
   - `LDO_02&BUCK_02` 对偶轨 → LDO\_12 + SW2 + LDO\_06（`_draw_vin_tree`，L2 + SW + 跨列对偶成员共享干线）
   - `LDO_13`（L1 单模块源）→ SW5/SW6（`_draw_sw_connections`，玫红干线 `SUB_BUS_X`，vin\_sw5\_6 药丸标记母线节点）
4. **并联对偶短接线**（紫色半透明，`_draw_pairs`）— BUCK↔LDO 输出端短接
   同列对偶（前 3 组）：两卡片均 `CARD_X_L1`，右边引短横线 → 竖线短接；
   跨列对偶（`BUCK_06↔LDO_06`）：`BUCK_06`@L1 输出横跨第二列，与 `LDO_06`@L2 输出
   在 `max(右边)+14` 处竖线短接，表示两路并联到同一轨
5. **子母线药丸**（深灰底 + 蓝字）

### 6.3 配色

独立于全局 theme（见 `docs/NewPlan/1811_Tool_UI.md`），主色：

- 琥珀 `#f59e0b` — VSYS 主轨
- 蓝 `#3b82f6` — 子母线级联
- 紫 `#a855f7` — 并联对偶输出短接
- 翡翠绿 `#10B981` — 使能/选中/数值

***

## 7. 外部接入

### 7.1 在主窗口中实例化

```python
from ui.pages.pmu.pmu_1811 import Pmu1811UI

self.pmu_1811_ui = Pmu1811UI()
self.instrument_ui_container_layout.addWidget(self.pmu_1811_ui)
```

### 7.2 PyInstaller 打包

`spec/kk_lab.spec` 的 `hiddenimports` 已注册全部子模块：

```python
'ui.pages.pmu.pmu_1811',
'ui.pages.pmu.pmu_1811.constants',
'ui.pages.pmu.pmu_1811.models',
'ui.pages.pmu.pmu_1811.workers',
'ui.pages.pmu.pmu_1811.page',
'ui.pages.pmu.pmu_1811.widgets',
'ui.pages.pmu.pmu_1811.widgets.toggle_switch',
'ui.pages.pmu.pmu_1811.widgets.module_card',
'ui.pages.pmu.pmu_1811.widgets.diagram_canvas',
'ui.pages.pmu.pmu_1811.widgets.property_panel',
'ui.pages.pmu.pmu_1811.widgets.context_menu',
```

### 7.3 独立预览

```powershell
python -m ui.pages.pmu.pmu_1811.page
```

***

## 8. 扩展指引

### 8.1 新增 LDO / BUCK

1. 在 `chips/bes1811_pmu.py` 添加寄存器映射（`LDO_REG_MAPS`）
2. 在 `models.py` 的 `_LAYOUT_ROWS` 增加一行 `LayoutRow`
3. `_default_modules()` 会自动从芯片表构建状态，无需改动

### 8.2 新增操作动作（如读取单 LDO）

1. 在 `core/bes1811_pmu_controller.py` 实现底层方法
2. 在 `workers.py` 复用 `LdoReadOneWorker` 或新增 Worker
3. 在 `page.py` 加触发点 + 信号回调

### 8.3 调整画布布局

- 改 `_LAYOUT_ROWS` 顺序/层级 → 自动重排
- 改 `constants.py` 几何常量 → 调整列距/行高
- 新增子母线：在 `_LAYOUT_ROWS` 加 `LayoutRow("bus", ...)` 并在 `DiagramCanvas.paintEvent` 调用 `_draw_subtree(parent_id)`

