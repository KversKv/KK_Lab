# KK'1811 PMU 配置工具

图形化配置 1811 PMIC：通过 USB 转 I2C（设备地址 0x17，10 位寄存器地址，16 位数据）控制各 LDO / BUCK 的使能、模式与输出电压。

本包按 **UI层 / 算法层 / 驱动中间层** 分离，取代早期单文件实现。

---

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
    ├── module_card.py       # 模块卡片 (LED + 名称 + 电压步进 + 齿轮)
    ├── diagram_canvas.py    # 拓扑画布 (VSYS / 子母线 / 卡片连线)
    ├── property_panel.py    # 属性面板 (使能/模式/电压/I2C/连接信息)
    └── context_menu.py      # 右键菜单 (使能切换 + 模式选择)
```

---

## 2. 分层职责

| 层 | 文件 | 职责 | 依赖方向 |
|---|---|---|---|
| **算法层** | `models.py` | 领域数据模型 + 拓扑布局 + 默认模块状态工厂（从 `chips/bes1811_pmu.py` 芯片寄存器表构建） | ← 依赖 `chips/` |
| **驱动中间层** | `workers.py` | QThread Worker，桥接 UI 与 `core/bes1811_pmu_controller.py`；每次操作自建/销毁 I2C 接口，避免跨线程共享 | ← 依赖 `core/` |
| **UI层** | `page.py` + `widgets/` | 纯 Qt 控件与页面编排，不直接访问硬件 | ← 依赖 `models` / `workers` |

依赖铁律（与项目分层一致 `main→ui↔core→instruments→lib`）：
- UI 层禁止阻塞 IO，必须通过 `workers.py` 走 QThread
- `workers.py` 不持有 Qt Widget 引用，只发射 Signal
- `models.py` 不依赖 Qt

---

## 3. 核心数据模型

### 3.1 `PmuModule`（`models.py`）

单个 LDO / BUCK 模块的运行时状态：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 模块标识，如 `LDO_01` / `BUCK_03` |
| `type` | str | `"LDO"` 或 `"BUCK"` |
| `enabled` | bool | 使能状态 |
| `mode` | str | `Normal` / `LP`（BUCK 还支持 `ULP`） |
| `voltage` | float | 当前电压（V） |
| `min/max_voltage` | float | 电压范围（来自芯片表，已对齐 step） |
| `step` | float | 步进（来自 `chips/bes1811_pmu.get_ldo_step`） |
| `input` | str | 输入源（`VSYS` / `BUCK_01` / `vdd_l5` 等） |
| `controllable` | bool | 是否支持 I2C 寄存器控制（`is_ldo_controllable`） |

属性：
- `modes` — 返回该类型支持的模式列表
- `reg_map` — 从 `chips/bes1811_pmu.get_reg_map` 取回寄存器映射（`pu` / `vbit_normal` / `pu_status` 字段）

### 3.2 `LayoutRow`（`models.py`）

画布布局行，描述一行是模块还是子母线：

```python
LayoutRow(kind="module", id="LDO_01", level=1, input="VSYS")
LayoutRow(kind="bus",    id="vdd_l5", level=1, input="VSYS", bus_name="vdd_l5")
```

- `level=1` → 直连 VSYS，画在画布左列（`CARD_X_L1`）
- `level=2` → 二级支路，画在右列（`CARD_X_L2`），由子母线（蓝色）级联

### 3.3 `_LAYOUT_ROWS`

22 个模块 + 2 条子母线（`vdd_l14_15` / `vdd_l5`）+ 级联（`BUCK_01` → `LDO_12`）。

### 3.4 `_default_modules()`

从芯片寄存器表构建初始模块字典：
1. 调用 `is_ldo_controllable(id)` 判断是否支持 I2C
2. 通过 `get_voltage_range(id)` 取真实电压范围
3. 通过 `get_ldo_step(id)` 取 step，并用 `snap_range_to_step` 对齐 min/max
4. 默认电压：BUCK=1.0V，LDO=范围中点偏下并 `align_to_step`

---

## 4. 工作逻辑

### 4.1 启动流程

```
Pmu1811UI.__init__
  ├─ _default_modules()              # 从芯片表构建 22 个模块
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

| 触发源 | 信号 | page.py 处理 | 是否写 DUT |
|---|---|---|---|
| 卡片单击 | `canvas.module_selected` | `_on_select` | 否 |
| 卡片右键 | `canvas.module_right_clicked` | `_on_context` → 弹 `ContextMenu` | 否 |
| 卡片 +/− | `canvas.voltage_stepped` | `_on_card_voltage` | **是** (`voltage`) |
| 面板开关 | `panel.enable_changed` | `_on_panel_enable` | **是** (`enable`) |
| 面板模式 | `panel.mode_changed` | `_on_panel_mode` | **是** (`mode`) |
| 面板 Spin/Slider | `panel.voltage_changed` | `_on_panel_voltage` | **是** (`voltage`) |
| 右键菜单开关 | `menu.enable_toggled` | `_on_menu_enable` | **是** (`enable`) |
| 右键菜单模式 | `menu.mode_changed` | `_on_menu_mode` | **是** (`mode`) |
| Check 按钮 | clicked | `_on_check` | **是**（读全量） |

### 4.5 写入保护

`_start_write` 内部依次检查：
1. `mod.controllable == False` → 直接返回（无寄存器映射）
2. `_i2c_connected == False` → 仅本地更新，debug 日志
3. `_worker_thread is not None` → 上次操作未完成，丢弃并 WARN

Worker 完成后 `_cleanup_worker` 调用 `thread.quit() + wait()`，重置状态并恢复 Check 按钮。

---

## 5. I2C 驱动中间层

### 5.1 `workers.py` 三个 Worker

| Worker | 信号 | 用途 |
|---|---|---|
| `LdoReadAllWorker` | `finished(dict)` / `error(str)` / `log(str)` | 读取全部 LDO 状态 |
| `LdoReadOneWorker` | `finished(LdoState)` / `error` / `log` | 读取单个 LDO |
| `LdoWriteWorker` | `finished(ldo_id)` / `error` / `log` | 写入使能/模式/电压 |

### 5.2 关键约定（与 `core/bes1811_pmu_controller.py` 对齐）

- **每次操作自建/销毁控制器**：不持有持久 I2C 连接，避免跨线程共享问题
- **日志回调**：`_make_log_cb()` 把 controller 的 `(level, msg)` 包成 `"[LEVEL] msg"` 字符串发射 `log` 信号，主线程接到后直接 `execution_logs.append_log`
- **错误路径**：`connect()` 失败 → `error.emit("I2C 接口初始化失败")`；异常 → `logger.error(..., exc_info=True)` + `error.emit(str(e))`
- **`finally` 保证释放**：无论成功失败都 `ctrl.disconnect()`

### 5.3 连接参数

通过 `_dll_path` / `_speed_mode` 注入（当前 `page.py` 默认 `None` → 使用 controller 默认 DLL 与 100K 速率）。

---

## 操作规则集合（业务级）

LDO / DCDC / BUCK 等各类模块的使能状态判断、打开/关闭、模式切换、电压设置等实际硬件操作语义已单独整理至：

👉 [RULES.md](./RULES.md)

涵盖内容（按模块组织，后续可扩展）：
- **LDO** — 寄存器模型（9 个关键位域 `pu` / `pu_dr` / `pu_status` / `lp` / `lp_dr` / `vbit_*` / `res_sel_dr`）
  - 使能状态判断（依据 `dig_ldo_XX_pu` 状态位而非配置位 `pu`）
  - 打开/关闭 LDO 的两步写入流程
  - 模式切换、电压设置、读取流程、控制位/状态位语义对照
  - BUCK 与 LDO 的差异
- **DCDC** — 规划中
- **BUCK** — 寄存器模型（7 个位域, 无 `lp` / `lp_dr`, 有 `res_sel_dr`）+ 使能 + 电压已补全；模式切换待补全

---

## 6. 画布拓扑绘制

### 6.1 几何常量（`constants.py`）

| 常量 | 含义 |
|---|---|
| `VSYS_X` | VSYS 主母线 x 坐标 |
| `CARD_X_L1` / `CARD_X_L2` | 一级 / 二级卡片 x 坐标 |
| `SUB_BUS_X` | 子母线竖线 x 坐标 |
| `CARD_W` / `CARD_H` / `ROW_H` / `TOP_PAD` | 卡片与行距 |
| `BUS_PILL_W` / `BUS_PILL_H` / `BUS_PILL_X` | 子母线药丸尺寸与位置 |

### 6.2 绘制层次（`DiagramCanvas.paintEvent`）

1. **VSYS 主母线**（琥珀色实线）— 跨所有 VSYS/bus 行
2. **一级 → VSYS 横线**（琥珀色半透明）— 每行一条
3. **子母线**（蓝色半透明，`_draw_subtree`）：
   - `vdd_l14_15` → LDO_14/15/VMIC1/VMIC2
   - `vdd_l5` → LDO_05/13
   - `BUCK_01` → LDO_12（级联，从父卡片右边引出）
4. **子母线药丸**（深灰底 + 蓝字）

### 6.3 配色

独立于全局 theme（见 `docs/NewPlan/1811_Tool_UI.md`），主色：
- 琥珀 `#f59e0b` — VSYS 主轨
- 蓝 `#3b82f6` — 子母线级联
- 翡翠绿 `#10B981` — 使能/选中/数值

---

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

---

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
