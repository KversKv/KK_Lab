# ui/pages/pmu/pmu_1811 — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../../AGENTS.md) 硬红线。本文件由 README + RULES 整合而来，是 1811 PMU 页的单一事实源。

## 加载指针（AI 按需拉取）

- **Qt / UI 通用规范** → @see [docs/ai/01_CONVENTIONS.md §6](../../../../docs/ai/01_CONVENTIONS.md)
- **I2C 底层 / DLL** → @see [docs/ai/03_GOTCHAS.md §11](../../../../docs/ai/03_GOTCHAS.md)
- **寄存器数据源** → `ui/pages/pmu/pmu_1811/data/1811 pmu inf reg.csv`、`BES1811 LDO输出电压范围.csv`
- **芯片寄存器表** → [chips/bes1811_pmu.py](../../../../chips/bes1811_pmu.py)
- **UI 设计稿** → `docs/NewPlan/1811_Tool_UI.md`

## 本模块职责与边界

图形化配置 BES1811 PMIC：经 USB 转 I2C（**设备地址 0x17，10 位寄存器地址，16 位数据**）控制各 LDO / BUCK / SW 的使能、模式与输出电压。

**三层分离**（取代早期单文件实现）：

| 层 | 文件 | 职责 | 依赖方向 |
|---|---|---|---|
| 算法层 | `models.py` | `PmuModule` / `LayoutRow` / 拓扑布局 / 默认状态工厂（从 chips 寄存器表构建） | ← `chips/` |
| 驱动中间层 | `workers.py` | QThread Worker，桥接 UI 与 `core/bes1811_pmu_controller.py`；**每次操作自建/销毁 I2C 接口**，避免跨线程共享 | ← `core/` |
| UI 层 | `page.py` + `widgets/` | 纯 Qt 控件与页面编排，不直接访问硬件 | ← `models` / `workers` |

铁律：UI 禁阻塞 IO 必须走 `workers.py` 的 QThread；`workers.py` 不持 Qt Widget 引用只发 Signal；`models.py` 不依赖 Qt。

## 接口契约（对外不可破坏）

- **对外导出**：`Pmu1811UI`（`__init__.py`）。主窗口 `Pmu1811UI()` 实例化嵌入；独立预览 `python -m ui.pages.pmu.pmu_1811.page`。
- **Worker 四件套**（`workers.py`）：`LdoReadAllWorker` / `LdoReadOneWorker` / `LdoWriteWorker` / `PairWriteWorker`；信号统一 `finished/error/log`。
- **三种写入动作**（`LdoWriteWorker.action`）：`"enable"` / `"mode"` / `"voltage"`。
- **打包**：`spec/kk_lab.spec` 的 `hiddenimports` 已注册全部子模块（含 `widgets/*`）。

## 核心数据模型

- **`PmuModule`**：单模块运行时状态。字段 `id / type(LDO|BUCK|SW) / enabled / mode / voltage / min|max_voltage / step / input / controllable / rdson(SW) / output(SW)`。属性 `modes` / `reg_map` / `sw_reg_map`。
- **`LayoutRow`**：画布布局行 `kind="module"|"bus"`，`level=1` 直连 VSYS（左列 `CARD_X_L1`）、`level=2` 二级支路（右列 `CARD_X_L2`）；`pair` 为并联对偶伙伴。
- **`_LAYOUT_ROWS`**：22 模块 + 2 子母线（`vdd_l14_15` / `vdd_l5`）+ 7 个 SW；**4 组并联对偶**（输出短接、互斥使能）：`BUCK_01↔LDO_01`、`BUCK_02↔LDO_02`、`BUCK_03↔LDO_03`、`BUCK_06↔LDO_06`（跨列对偶）。对偶表 `models._PAIRS`，查询 `get_pair_partner(id)`。
- **`_default_modules()`**：`is_ldo_controllable` → `get_voltage_range` → `get_ldo_step` + `snap_range_to_step` 对齐；默认电压 BUCK=1.0V、LDO=范围中点偏下并 `align_to_step`。

## 局部约定

### 使能/模式/电压语义（核心，勿踩坑）

- **LDO/BUCK 使能判断读 `pu_status` 状态位**（`dig_ldo_XX_pu` / `dig_buck_XX_pu`），**不读配置位 `pu`**——`pu=1` 但 `pu_dr=0` 时硬件未必真开。`pu_status` 才是真实反馈。
- **SW 无独立状态位**，直接读 `en` 配置位（`en_dr=0` 时 `en` 不生效，语义后续讨论）。
- **写入两步固定顺序**：先置驱动位 `pu_dr=1`（或 `en_dr=1` / `lp_dr=1`）→ 再写配置位。
- **LDO 电压 3 步**：查表取 vbit → 写 `vbit_normal` → 若 `res_sel_dr==0` 置 1。
- **BUCK 电压 5 步**（专用）：`bg_en_dr=1,bg_en=1` + delay 1ms → `sw_en=1` → 写 vbit + `res_sel_dr=1` → `sw_en=0` + delay → `bg_en=0`。前后序列由 `_buck_voltage_pre_seq` / `_buck_voltage_post_seq` 实现，LDO 无此字段会自动跳过。
- **三档电压**：Normal / Deep Sleep / RC 分别对应 `vbit_normal` / `vbit_dsleep` / `vbit_rc`，共用同一查找表，写入流程一致。
- **vbit 索引进制**：LDO = **十六进制**（`LDO_VOLTAGE_TABLES` 索引为 hex，源 xlsx 含 A-F）；BUCK = **十进制**（`BUCK_VOLTAGE_TABLES` 索引为 dec，256 档连续）。
- **写入后 UI 立即更新本地状态是"期望状态"**；真实状态需 Check 重读 `pu_status` 才反映。这是 `enabled` 在写入/读取两路径都被赋值的原因。

### SW 默认状态规则

- 默认表 `models._SW_DEFAULT_ENABLED`：**SW1/3/5/6 闭合、SW7/2/4 开路**；查询 `sw_default_enabled(id)`，`_default_modules()` 据此设 `PmuModule.enabled`。
- **"规则匹配" = SW 可控**（在 `SW_REG_MAPS` 中）：Check 成功后 `LdoReadAllWorker._apply_sw_defaults` 对每个可控 SW 调 `set_sw_enabled` 主动写 `en_dr=1, en=1/0`（强制闭合/开路，RULES §3），写后重读 `read_sw` 回灌 `states`；单个失败仅 WARN 不中断。
- 不可控 SW 不主动写，仅用默认表作本地显示。page `_on_read_all_done` 末尾兜底刷新全部 SW 卡片。

### 并联对偶互锁

开启某模块且存在对偶 → 走 `PairWriteWorker`，**一次 I2C 会话内先开自己、再关对偶**；关闭走普通 `LdoWriteWorker` 不影响对偶。未连接时仅本地更新（`_apply_local_disable`）。

### VMIC (LDO_VMIC1/2) 特例

- VMIC 走独立 `VMIC_REG_MAPS`（`VmicRegMap`），**不在** `LDO_REG_MAPS`；判定 `is_vmic(id)`，查询 `get_vmic_reg_map(id)`。
- **无 pu_status / lp / res_sel_dr / vbit 三档**；使能 = `mic_ldoX_en`（0x039[11]/[10]）+ `mic_biasX_en`（0x03B/0x03C[13]）双配置位均 1（读配置位判定，同 SW 语义）。
- **开启序列**（`set_vmic_enabled(True)`，与脚本 vmicX_on 一致）：EN VCM（共用：0x365[13]=0 → 0x365[12]=1 → 0x364[13]=1）→ EN MIC_LDO（0x122 lp_enable=1 → 0x06D dr=1 → 0x039 en=1）→ EN MIC_BIAS（0x03B/C[12:10]=0x4 → en=1）。**关闭**仅写 `mic_ldoX_en=0` + `mic_biasX_en=0`。
- 电压仅一档：`reg_mic_biasX_vsel`（0x074/0x075[13:9]，5 bit），表在 `VMIC_VOLTAGE_TABLES`（VMEM=1.8V 工况；VMIC2 的 vsel 0x10/0x11 无数据为 None）。注意 **0x074[7:0] 与 BUCK_01 vbit_rc 同寄存器不同位**，RMW 不冲突。
- UI：`modes=["Normal"]`；属性面板隐藏 dsleep/rc 电压卡（`_multi_volt_widgets`）；Worker 仅支持 `enable` / `voltage`，其余 action WARN 忽略。
- `BUCK_01~06` 模式切换（Normal/LP/ULP）仍待补全（写入 WARN 忽略）。

### BUCK 寄存器特例

- `BUCK_01` 的 `vbit_normal` / `vbit_dsleep` 共用 0x046（低/高字节）；`vbit_rc` 在 0x074（RWS 写后自清）。
- `BUCK_06` 的 `vbit_dsleep` 地址 0x35C 跳过 0x35B。
- 状态位 0x05F 与 LDO 共用：bit[0..7]=LDO_01~08、bit[8..13]=BUCK_01~06；`res_sel_dr` 共用 0x2F0（BUCK 占 bit[0..5]）。
- BUCK 模式切换（Normal/LP/ULP）**待补全**；DCDC **规划中**。

### 画布绘制

- 几何常量集中在 `constants.py`（`VSYS_X` / `CARD_X_L1|L2|L3` / `SUB_BUS_X` / `SW_BUS_X` / 卡片与药丸尺寸）。
- 配色独立全局 theme：琥珀 `#f59e0b`(VSYS)、蓝 `#3b82f6`(子母线)、紫 `#a855f7`(对偶短接)、翡翠绿 `#10B981`(使能)、玫红 `#ec4899`(SW)。
- SW 由 `SwitchWidget` 画拟物开关（非卡片）：输入引线、左右玫红端点、动态连杆（闭合=绿水平/开路=灰上倾28°），单击切换。

### 图标与独立预览

- **页面图标**：`resources/pages/pmu_1811_SVGs/pmu_1811.svg`（emerald 渐变芯片图）；渐变色图标必须走 `ui/utils/icon_utils.svg_pixmap()` **原色渲染**，禁用 tinted 版本（`SourceIn` 会把渐变染成单色）。spec 按 `resources/pages` 整目录打包，新增子目录无需改 spec。
- **独立预览壳**（`page.py` `__main__`）：参考 main 窗口不用系统标题栏，`FramelessWindowHint | Qt.Window` + `_PreviewTitleBar` 自绘标题栏（1811 主题色）；拖动走 `windowHandle().startSystemMove()`，最大化手动切 `availableGeometry`（避免 frameless `showMaximized` 盖住任务栏）。
- **frameless 无系统边框缩放**：壳需 `setMouseTracking(True)` + 事件过滤器 + `startSystemResize`。三个坑：① 过滤器要装到 **QApplication**（边缘处鼠标实际落在子控件上，shell 自身收不到）；② 坐标用 `obj.mapTo(shell, pos)` 换算；③ 光标用 `obj.setCursor()` 设在悬停控件上（override 光标会被各控件自身光标覆盖）；④ 边缘组合必须 `edges = Qt.Edge(0)` 起始再 `|=`（用 int `0` 起始在 PySide6 下 `int |= Edge` 直接 TypeError，这是过滤器静默崩溃、光标全没跑的根源）。过滤器内先做 `isinstance(obj, QWidget)` 防护（QApplication 会收到 QWindow/QStyle 等非 QWidget 对象，`isAncestorOf` 会 TypeError）。
- **纯 QWidget 不绘 QSS 背景**：壳与 `_PreviewTitleBar` 这类直接继承 `QWidget` 的控件，必须 `setAttribute(Qt.WA_StyledBackground, True)` 才会按 QSS 绘制背景，否则露 Fusion 默认白底（QFrame 子类无此问题）。

## 局部坑点

- **写入保护**（`_start_write`）：`controllable==False` 直接返回；`_i2c_connected==False` 仅本地更新；`_worker_thread is not None` 丢弃并 WARN（上次未完成）。Worker 完成 `_cleanup_worker` 必须 `thread.quit() + wait()`。
- **每次操作自建/销毁 controller**：不持持久 I2C 连接；`finally` 保证 `ctrl.disconnect()`。
- **首次显示自动 Check**：`showEvent` 用 `QTimer.singleShot(0, self._on_check)` 等 UI 布局完成后再起 `LdoReadAllWorker`。
- **Check 失败锁定画布**：`_on_i2c_error` → `_set_body_blocked(True)`，用 `_BlockedOverlay`（半透明遮罩，父=`_body_container`）盖住画布+属性面板拦截交互；`_on_read_all_done` → `_set_body_blocked(False)` 解锁。遮罩几何在 `resizeEvent` 里跟随 `_body_container.rect()`。
- **独立运行**：顶部已注入 `sys.path`（兼容 `python ui\pages\pmu\pmu_1811\page.py` 直接运行，见 03§22 同款模式）。

## 扩展指引

- **新增 LDO/BUCK**：`chips/bes1811_pmu.py` 加寄存器映射 → `models._LAYOUT_ROWS` 加 `LayoutRow` → `_default_modules()` 自动构建。
- **新增操作动作**：`core/bes1811_pmu_controller.py` 实现底层 → `workers.py` 复用/新增 Worker → `page.py` 加触发点+回调。
- **调整画布布局**：改 `models._LAYOUT_ROWS` 行序与 `level` / `pair`；几何改 `constants.py`。

> 历史参考：原始 README.md / RULES.md 已整合进本文件；详细位域地址表（LDO 9 域 / BUCK 11 域 / SW 2 域一览）见 `data/` CSV 与 `chips/bes1811_pmu.py`。
