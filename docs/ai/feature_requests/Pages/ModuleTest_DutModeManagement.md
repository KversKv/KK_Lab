# Module Test — DUT 工作模式管理方案（LDO / DCDC）

> 类型：对现有 Module Test（LDO/DCDC 子页面）的**增量设计**，聚焦"DUT 工作模式 / Bias 如何在测试中被声明、进入与遍历"。
> 本文只做**规划**，不动代码。落地时严格遵循 [06_PAGE_GUIDE](../../06_PAGE_GUIDE.md) / [01_CONVENTIONS §6](../../01_CONVENTIONS.md) / [03_GOTCHAS](../../03_GOTCHAS.md) / [05_INSTRUMENT_GUIDE](../../05_INSTRUMENT_GUIDE.md) / [04_ARCHITECTURE](../../04_ARCHITECTURE.md)。
> 前置总规划：[newModuleTest.md](./newModuleTest.md)。本文补齐其 §2 中 `ldo_quiescent` / `dcdc_quiescent` 的"各模式 Iq"如何真正覆盖所有 CASE。

---

## 1. 问题定义

LDO / DCDC 在实际使用中存在多种**工作模式**，且模式（含 bias 挡）会直接影响绝大部分测试项的结果（静态电流、纹波、效率、瞬态响应等），而不仅是 Quiescent Current 一项。

### 1.1 典型模式矩阵（以 DUT 举例）
| 器件 | 模式 | 语义 | 静态电流量级 |
|---|---|---|---|
| LDO | LP Mode | 低功耗 | 最低 |
| LDO | Normal Mode（含 bias 可调） | 正常，bias 权衡功耗/性能 | 中~高，随 bias 变化 |
| DCDC | ULP Mode | 极低功耗，对应 SOC 睡眠 | 最低 |
| DCDC | Burst Mode | 正常工作，中等静态电流 | 中 |
| DCDC | PWM Mode | 高负载，保证响应/纹波 | 最高 |

### 1.2 三类"进入模式"的 CASE（核心矛盾点）
现状代码（[ldo/items `quiescent`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/ldo/items/__init__.py#L127-L159)、[dcdc/items `quiescent`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/dcdc/items/__init__.py#L200-L232)）把 `iq_modes` 当作一个"逗号分隔文本框"，且注释写明"模式切换由外部配置寄存器 / 测试台完成"。这只覆盖了"人已手动切好、工具只采集"的场景，无法覆盖：

| CASE | 谁负责切模式 | 工具需要做什么 |
|---|---|---|
| **A. 寄存器可控** | 工具写 I2C 寄存器 | 遍历模式 → 每模式写寄存器（LDO 含 bias 值）→ settle → 测量 |
| **B. 负载自动切换** | 由负载电流决定（部分 DCDC 自动 ULP/Burst/PWM） | 遍历负载点 → settle → 回读芯片"当前实际模式" → 记录 Iq + 实际模式 |
| **C. 手动台架** | 人手动改（无 I2C 或专用治具） | 逐模式**暂停**等待用户确认改好 → 测量 |

一个纯文本框覆盖不了 B 和 C；且模式是**跨测试项的共性配置**，不应只塞在 quiescent 一项的参数弹窗里。

---

## 2. 设计目标与非目标

### 2.1 目标
1. 在**被测配置区（基类级）**新增一个"DUT 工作模式管理区"，作为跨测试项共享的模式声明源。
2. 每个模式可声明其**进入方式**（`reg` / `load` / `manual`），一套结构统一吃下 CASE A/B/C。
3. 测试项（首批：quiescent；后续可推广到 ripple/efficiency/transient）按声明的模式列表遍历，结果统一带 `Mode` 维度落盘与进报告。
4. 保持"一次执行产出合并报告"的既定闭环，不回退为"用户手动切一个模式跑一遍"。
5. 全链路 Mock 可空跑；AI 契约新增"模式维度"可读、可回填。

### 2.2 非目标（本期不做）
- 不新增仪器驱动；I2C 写寄存器复用现有 [_common.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/_common.py) 的 I2C 接口创建逻辑（`create_i2c`）。
- 不实现"AI 自主现场决定寄存器序列"；AI 只做**编排/判读**（详见 §7）。
- 不改报告的整体框架，仅在数据模型里增加 `mode` 维度字段。

---

## 3. 分层落点与"谁做什么"

沿用铁律 `main → ui ↔ core → instruments → lib`，模式切换属于**确定性硬件逻辑**，放在 core，不放 AI、不放 UI：

```
被测配置区(UI, 基类)  ──声明模式清单──►  cfg["dut_modes"]（结构化列表）
                                            │
core/module_test/mode_manager.py  ◄─────────┘  解析 & 提供"进入模式"原子能力
   ├─ enter_mode_reg(ctx, mode_spec)   # CASE A：写 I2C 寄存器（LDO 含 bias）
   ├─ enter_mode_load(ctx, mode_spec)  # CASE B：设负载点 + 回读实际模式
   └─ enter_mode_manual(ctx, mode_spec)# CASE C：发暂停信号等用户确认
                                            │
items/quiescent(ctx)  ──按 mode.enter 分派──┘  逐模式：进入→settle→测量→记录
```

**决策依据**：把"如何进入某模式"做成 core 的稳定原子能力，保证可复现、可回归、Mock 可跑；上层（人或 AI）只决定"测哪些模式组合"。这与项目"AI 编排 + 工具执行"的分工一致，也符合 [04_ARCHITECTURE](../../04_ARCHITECTURE.md) 对 core 不反依赖 UI 的要求。

---

## 4. 数据结构：模式声明（`dut_modes`）

在全局 cfg 中新增一个键 `dut_modes`，为模式声明列表；每个元素形如：

```python
# 概念结构（落地时用 dataclass 或纯 dict，与现有 cfg 均为 dict 保持一致）
{
  "name": "Normal_biasH",      # 模式显示名（唯一，进报告 / CSV 的 Mode 列）
  "enter": "reg",              # 进入方式：reg | load | manual
  # —— enter == "reg"（CASE A）——
  "reg_writes": [              # 顺序写入的寄存器列表（含 bias 挡位）
      {"addr": "0x30", "value": "0x02"},   # 选模式
      {"addr": "0x31", "value": "0x0F"},   # bias 挡
  ],
  # —— enter == "load"（CASE B）——
  "load_ma": 50.0,             # 触发该模式的负载电流点
  "mode_readback": {           # 可选：回读芯片当前模式的寄存器 + 期望值/位段
      "addr": "0x40", "msb": 1, "lsb": 0, "expect": 2
  },
  # —— enter == "manual"（CASE C）——
  "prompt": "请手动将 DUT 切到 PWM 模式后点击确认",
  # —— 通用可选 ——
  "settle_s": 0.2,             # 该模式额外稳定时间（覆盖项级默认）
}
```

要点：
- 三种 `enter` 的字段互斥，仅取用当前类型对应字段；解析时缺字段给合理默认并 `log` 警告，不抛裸异常。
- `name` 唯一，是结果表 `Mode` 维度、报告分组与 AI 引用的 key。
- 地址/位段沿用现有 `reg_scan_params` 的 `0xNN` 文本 + msb/lsb 约定，保持一致（禁硬编码地址，走配置）。

---

## 5. UI 设计：被测配置区新增"DUT 工作模式管理区"

### 5.1 位置与范式
在 [`_build_config_group()`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/module_test/_base_subpage.py#L237) 内、"高低温测试"区块之上或之下，新增一个**折叠子区**，复用现有"高低温测试勾选后展开"的成熟联动范式（[`_on_temp_test_toggled`](file:///d:/CodeProject/TRAE_Projects/KK_Lab/ui/pages/module_test/_base_subpage.py#L338-L342)）。

因"一个框不够"（用户明确），采用**小型模式表格 + 增删按钮**的区域式布局：

```
被测配置
 ├─ 芯片/模块/操作员/通道/... （现有）
 ├─ [☑] 高低温测试  → 展开温度设置（现有）
 └─ ── DUT 工作模式管理 ─────────────────────────────
     ┌──────────────────────────────────────────────┐
     │ 模式名        进入方式   关键参数摘要      [编辑]│  ← QTableWidget
     │ LP           reg       0x30=0x00              │
     │ Normal_biasH reg       0x30=0x02;0x31=0x0F    │
     │ Burst(自动)  load      50 mA  回读0x40[1:0]==1 │
     │ PWM(手动)    manual    提示: 手动切PWM         │
     └──────────────────────────────────────────────┘
     [+ 添加模式]  [编辑]  [删除]        默认基准模式: [Normal_biasH ▾]
```

- 表格只读摘要；增/编辑走**弹窗**（`QDialog`，`parent=self`，OK/Cancel 显式 default/autoDefault，遵铁律），弹窗内按 `enter` 类型动态显示对应字段（reg 表 / load 输入 / manual 提示）。
- "默认基准模式"下拉：供**未声明模式遍历的测试项**使用（如 efficiency/ripple 默认只在该模式下测，避免每项重填）。这落地了用户"想法1"的合理部分——全局基准，但不牺牲 quiescent 的多模式遍历能力。
- 复用控件高度铁律：区内 `QComboBox/QPushButton` 用自身 `#objectName` 钉 `min-height:22px`，禁页面父级裸 `min-height`。
- 数值标签带单位：`负载 (mA)`、`稳定 (s)` 等。

### 5.2 与测试项的关系（避免全局单模式的僵化）
- **quiescent 项**：默认遍历"模式管理区"里**所有**模式（去掉了原 `iq_modes` 文本框，改为读 `dut_modes`）。
- **其它项（ripple/efficiency/transient/...）**：默认只在"默认基准模式"下跑；若某项需要多模式对比，可在该项参数弹窗勾选"遍历模式（多选自 dut_modes）"。
- 这样：模式是**基类共享声明**，而"哪个项遍历哪些模式"是**项级选择**，两级解耦，既覆盖全流程合并报告，又不失灵活。

---

## 6. core 编排改动

### 6.1 新增 `core/module_test/mode_manager.py`
提供无 Qt 依赖的纯函数（对齐 [_common.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/_common.py) 风格）：

```python
def parse_dut_modes(cfg) -> list[ModeSpec]: ...        # 解析 cfg["dut_modes"]
def enter_mode(ctx, mode: ModeSpec) -> ModeEntryResult:
    # 按 mode.enter 分派：
    #   reg    → 逐条写 I2C（create_i2c 复用），失败记录并 return 失败态
    #   load   → set_load_current + settle + 可选回读实际模式
    #   manual → ctx.pause_fn(prompt) 阻塞等待确认（见 §6.3）
    # Mock 模式：全部跳过硬件，返回 mock 实际模式
```

`ModeEntryResult` 至少含：`ok: bool`、`actual_mode: str`（B 场景回读结果，A/C 即 name）、`note: str`。

### 6.2 改造 `quiescent`（LDO + DCDC）
现状逐 `iq_modes` 文本项循环，改为：

```
modes = parse_dut_modes(ctx.config)          # 取代 cfg["iq_modes"]
for mode in modes:
    if ctx.stop_flag_fn(): break
    entry = enter_mode(ctx, mode)            # 覆盖 A/B/C
    settle(ctx, mode.settle_s or 项级默认)
    iq = measure_avg(ctx, "measure_current", vin_ch, ...) * 1e6
    rows.append([mode.name, entry.actual_mode, mode.enter, round(iq, 3)])
```

- CSV 表头由 `["Mode","Iq (uA)"]` 扩为 `["Mode","ActualMode","EnterBy","Iq (uA)"]`。
- CASE B（load）下 `ActualMode` 记录回读到的真实模式，便于发现"预期 Burst 实际落在 PWM"这类问题。
- 保留 `average_cnt` / `settle_time_s` 项级参数不变；删除旧 `iq_modes` 文本 `ParamSpec`（[ldo #L556](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/ldo/items/__init__.py#L556) / [dcdc #L758](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/module_test/dcdc/items/__init__.py#L758)）。

### 6.3 手动模式（CASE C）的暂停机制
Runner（QThread）需要一个"请求 UI 弹确认、线程阻塞等待"的协作通道：
- Runner 新增信号 `mode_confirm_required(str prompt)`；`ItemContext` 增 `pause_fn(prompt)`，内部用 `QWaitCondition`/事件等待，UI 侧弹 `QMessageBox`（`parent=self`）确认后释放。
- 必须响应 `stop_flag`：等待期间用户点停止要能退出（禁死等）。
- Mock 模式跳过暂停，直接放行。

### 6.4 结果模型
`ItemResult.measured` 已是 dict/list，天然容纳新增列，**无需改 `result_model.py` 结构**；仅报告渲染（[report.py 思路](file:///d:/CodeProject/TRAE_Projects/KK_Lab/docs/ai/feature_requests/Pages/newModuleTest.md)）在 quiescent 段按 `Mode` 分组展示即可。

---

## 7. AI Assistant 的定位（回应用户"想法2"）

**结论：最优解是"AI 编排 + 工具执行"，不是让 AI 现场切模式。**

- 底层确定性（写哪个寄存器、settle 多久、如何回读）交给 §6 的 `mode_manager` 原子能力 —— 保证可复现、可回归、Mock 可跑。
- AI 负责上层不确定/需判断的部分：
  - 依据芯片/规格，**生成 `dut_modes` 草案**（哪些模式、bias 挡、对应寄存器），经 `ai_apply_config` 走确认闭环回填到"模式管理区"（复用现有高亮 + `[AI]` 日志，见 [newModuleTest §8.4](./newModuleTest.md)）。
  - 跑完后**判读跨模式结果**（如"ULP 8µA 偏高，疑似漏电"），读 `ai_get_result_summary`。
- 契约扩展（对齐 [newModuleTest §8](./newModuleTest.md)，均为改现有方法、不改 core 契约框架）：
  - `ai_get_config()`：在返回的"会遍历维度"里包含 `dut_modes`（仅当勾选了 quiescent 或有项开启多模式遍历时才计入，避免误导 AI 臆造组合）。
  - `ai_apply_config(payload)`：支持写入 `dut_modes`；运行中拒绝改。

> 若纯靠 AI 现场决定寄存器序列，会把硬件时序确定性塞进不确定的 AI，回归性差、Mock 难覆盖，故不采纳。

---

## 8. Mock / 回归

- `DEBUG_MOCK=True`：`enter_mode` 全部跳过硬件；`reg` 直接返回声明模式，`load` 返回按负载映射的 mock 实际模式，`manual` 不暂停；quiescent 按各模式量级产出 mock Iq（沿用现有 `{"PWM":200,"BURST":60,"ULP":8}` 等映射思路）。
- 手动回归清单：
  - [ ] 被测配置区出现"DUT 工作模式管理区"，增/删/编辑模式弹窗正常（OK/Cancel 二元化，`parent=self`）。
  - [ ] reg 模式：真机逐条写寄存器成功，日志可见地址/值。
  - [ ] load 模式：负载点生效，`ActualMode` 回读正确记录。
  - [ ] manual 模式：弹确认框，确认后继续，测试中"停止"能中断等待。
  - [ ] quiescent CSV 含 `Mode/ActualMode/EnterBy/Iq(uA)` 四列，报告按模式分组。
  - [ ] "默认基准模式"对未遍历模式的项生效。
  - [ ] AI apply_config 可回填 dut_modes 并高亮；get_config 只在相关项勾选时暴露模式维度。
  - [ ] lint 通过；无 `print`、无裸 `except`、`mode_manager` 无 Qt 依赖、UI 无阻塞 IO。

---

## 9. 同步矩阵（落地后必更）

依据 [08_CHECKLISTS 同步矩阵](../../08_CHECKLISTS.md) 与项目规则 §4：
- [ ] `DIRECTORY_STRUCTURE.txt`：新增 `core/module_test/mode_manager.py`。
- [ ] `helps/module_test_ldo.html` / `module_test_dcdc.html`：补"DUT 工作模式管理"使用说明与三类进入方式。
- [ ] `core/ai/providers/page_provider.py` / `core/ai/profiles.py`：如 §7 契约措辞需要，同步 profile 引导（不新建文件）。
- [ ] `docs/kk_lab_ai_memory/automation/module_test/`：在 test_items 记录 quiescent 多模式方法与 lessons（load 回读不符预期等坑）。
- [ ] `docs/ai/memory.md`：沉淀"模式作为基类共享声明 + 三类进入方式 + AI 只编排"的决策。
- [ ] `docs/ai/decisions/`：记录"模式管理放基类而非全局单模式"、"AI 编排而非现场切模式"两项取舍。

---

## 10. 实施顺序建议（后续动代码时）

1. `core/module_test/mode_manager.py`：`parse_dut_modes` + `enter_mode`（先 Mock 分支跑通）。
2. UI：被测配置区"DUT 工作模式管理区" + 编辑弹窗 + `get_config/apply_config` 读写 `dut_modes` + 默认基准模式下拉。
3. 改造 LDO/DCDC `quiescent`：读 `dut_modes` 遍历，扩展 CSV 列；删旧 `iq_modes` 文本 ParamSpec。
4. Runner 暂停通道（`mode_confirm_required` + `pause_fn`），支持 stop 中断。
5. 报告 quiescent 段按 Mode 分组渲染。
6. AI 契约 `get_config/apply_config` 纳入 `dut_modes`；补记忆库与决策记录。
7. （可选推广）为 ripple/efficiency/transient 项加"遍历模式（多选）"开关。
