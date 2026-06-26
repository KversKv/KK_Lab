# KK Lab AI 记忆体系写入规范

> 本文件是 KK Lab AI 记忆体系的唯一规范源：目录结构、页面键白名单、文件职责、写入模板、
> ID 规则、字段规范与安全规则。AI Assistant 受控写入与人工维护均须遵守本规范。

---

## 1. 适用范围

- 项目级目录：`docs/kk_lab_ai_memory/`（随包、纳入版本控制、人工审查）。
- 本机私有目录：`user_data/ai/kk_lab_ai_memory/`（开发态私有、运行时自动沉淀、默认不入版本控制）；
  打包后对应 `%APPDATA%/KK_Lab/ai/kk_lab_ai_memory/`。
- 本机私有层文件名统一加 `.local` 后缀，如 `lessons.local.md`。
- AI Assistant 写入时优先写本机私有层；用户确认有复用价值后再提升为项目级文档。

## 2. 页面键白名单

页面目录名**唯一来源**为 `MainWindow._get_current_help_key()`，禁止另造命名体系。
以下 19 个页面键为合法白名单，未知页面写入 `_shared/pending.md` 或拒绝。

| 页面 / 子页面 | 目录键 |
|---|---|
| N6705C 电源分析仪 | `power_analyser` |
| N6705C Datalog | `datalog` |
| 示波器 | `oscilloscope` |
| 温箱 | `thermal_chamber` |
| 串口工具 | `kk_serials` |
| 采集集合 | `collection` |
| Orchestrator | `orchestrator` |
| VminHunter | `vmin_hunter` |
| 功耗测试 | `consumption_test` |
| PMU DCDC 效率 | `pmu_dcdc_efficiency` |
| PMU 输出电压 | `pmu_output_voltage` |
| PMU Is Gain | `pmu_is_gain` |
| PMU OSCP | `pmu_oscp` |
| PMU GPADC | `pmu_gpadc` |
| PMU CLK | `pmu_clk` |
| Charger 配置遍历 | `charger_config_traverse` |
| Charger 状态寄存器 | `charger_status_register` |
| Charger Iterm | `charger_iterm` |
| Charger 调节电压 | `charger_regulation_voltage` |

## 2.1 伞目录键（umbrella）

除页面键外，允许少量**伞目录键**承载跨页面的同一业务簇总记忆（例如 PMU 整套常规测试
横跨 `pmu_output_voltage` / `pmu_dcdc_efficiency` / `pmu_gpadc` / `pmu_oscp` / `pmu_clk` /
`pmu_is_gain` 等多个页面）。伞目录键不来自 `_get_current_help_key()`，仅由维护者在
`kk_lab_memory.py` 的 `_UMBRELLA_KEYS` 中登记，命名规则同页面键（小写 + 下划线，允许一级
`/` 分隔表达归类层级）。

| 伞目录（业务簇） | 目录键 | 说明 |
|---|---|---|
| PMU 整套常规测试总记忆 | `automation/pmu_test` | PMU 常规测试通用测试项、跨芯片差异、共性经验的总入口 |
| Charger 整套测试总记忆 | `automation/charger_test` | Charger 配置遍历 / 状态寄存器 / Iterm / 调节电压的总入口 |
| 电源分析仪簇总记忆 | `instrument/power_analyser` | N6705C 电源分析仪与 Datalog 子页面的总入口 |

伞目录与页面目录的关系：
- 伞目录写**通用 / 跨芯片 / 跨页面**的测试项与经验（总记忆）。
- 单个页面目录写**该页面专属**的测试项与经验（分记忆）。
- 二者通过条目 `关联项` 字段互相引用，避免重复堆砌。

### 物理目录归类（page_key 不变，按左侧导航 4 大组归类）

`page_key` 是 UI 动作命名空间 / AI 能力裁剪 / profiles 的键，**对外保持不变**
（仍是 `pmu_dcdc_efficiency` / `charger_iterm` / `power_analyser` 等，来源 `_get_current_help_key()`）。
为让磁盘结构与左侧导航栏一一对应，所有页面记忆目录在物理上按导航 4 大组归入对应一级父目录，
由 `kk_lab_memory.py` 的 `_DIR_OVERRIDE`（page_key → 记忆目录相对路径）映射，
读写函数 `project_dir` / `local_dir` 经 `_dir_rel()` 解析。一级父目录与导航分组对应关系：

| 导航分组 | 一级父目录 | 归入页面键 |
|---|---|---|
| INSTRUMENTS | `instrument/` | `power_analyser`、`datalog`（同属 N6705C 簇 `instrument/power_analyser/`）、`oscilloscope`、`thermal_chamber` |
| AUTOMATION | `automation/` | `pmu_*`（PMU 簇 `automation/pmu_test/`）、`charger_*`（Charger 簇 `automation/charger_test/`）、`consumption_test`、`vmin_hunter` |
| TOOLS | `tools/` | `kk_serials`、`collection` |
| ORCHESTRATION | `orchestration/` | `orchestrator` |

有子菜单的业务簇（PMU / Charger / N6705C）保留二级伞目录承载总记忆；其余页面直接放在一级父目录下。

```
instrument/                       # 导航 INSTRUMENTS
├── power_analyser/               # N6705C 簇伞目录（总记忆）
│   ├── power_analyser/           # page_key=power_analyser
│   └── datalog/                  # page_key=datalog
├── oscilloscope/                 # page_key=oscilloscope
└── thermal_chamber/              # page_key=thermal_chamber

automation/                       # 导航 AUTOMATION
├── pmu_test/                     # PMU 簇伞目录（总记忆）
│   ├── pmu_dcdc_efficiency/
│   ├── pmu_output_voltage/
│   ├── pmu_is_gain/
│   ├── pmu_oscp/
│   ├── pmu_gpadc/
│   └── pmu_clk/
├── charger_test/                 # Charger 簇伞目录（总记忆）
│   ├── charger_config_traverse/
│   ├── charger_status_register/
│   ├── charger_iterm/
│   └── charger_regulation_voltage/
├── consumption_test/             # page_key=consumption_test
└── vmin_hunter/                  # page_key=vmin_hunter

tools/                            # 导航 TOOLS
├── kk_serials/                   # page_key=kk_serials
└── collection/                   # page_key=collection

orchestration/                    # 导航 ORCHESTRATION
└── orchestrator/                 # page_key=orchestrator
```

## 3. 单页面文件职责

每个页面目录固定 5 个核心文件，第一版只维护这 5 类：

| 文件 | 记录内容 | AI 读取优先级 | 写入方式 |
|---|---|---|---|
| `memory.md` | 页面长期背景、稳定约定、页面参数含义、常见上下文 | 高 | 人工确认后追加或整理 |
| `lessons.md` | 踩坑、经验、排障结论、异常现象与处理办法 | 高 | AI 沉淀时追加条目 |
| `test_items.md` | 常用测试项、测试前置条件、检查项、人工操作清单 | 中 | AI 归档测试项时追加条目 |
| `test_cases.md` | 结构化测试用例：输入、步骤、期望、判定标准 | 中 | AI 归档测试用例时追加条目 |
| `quick_actions.md` | AI Assistant 页面快捷指令模板 | 高 | 迁移已有指令后由 AI 或人工追加 |

`_shared/` 用于跨页面共性内容：
- `conventions.md`：本文件，全局写入格式、字段规范、命名规则。
- `cross_page_lessons.md`：跨页面经验，例如仪器连接、日志分析、串口共性问题。

## 4. ID 规则

每条条目以二级标题 `## <前缀>-<YYYYMMDD>-<HHMMSS> - 标题` 起头，前缀按文件类型区分：

| 文件 | ID 前缀 | 示例 |
|---|---|---|
| `memory.md` | `M` | `M-20260625-143012` |
| `lessons.md` | `L` | `L-20260625-143012` |
| `test_items.md` | `T` | `T-20260625-143012` |
| `test_cases.md` | `TC` | `TC-20260625-143012` |
| `quick_actions.md` | `QA` | `QA-20260625-143012` |

- 时间戳取写入时刻，保证全文件唯一。
- 从 `AI_PROFILES[*].quick_actions` 迁移而来的条目使用 `QA-20260625-<序号>` 形式，
  `来源` 字段标记为 `profile_migration`。
- 跨页面共性条目写在 `_shared/cross_page_lessons.md`，ID 前缀仍为 `L`。

## 5. 写入模板

### 5.1 memory.md

```markdown
## M-YYYYMMDD-HHMMSS - 标题

- 页面：power_analyser
- 来源：ai_assistant / manual
- 稳定性：stable / tentative
- 摘要：一句话说明这条记忆解决什么问题
- 内容：
  - ...
- 适用条件：
  - ...
- 关联项：
  - lessons: L-...
  - test_items: T-...
```

### 5.2 lessons.md

```markdown
## L-YYYYMMDD-HHMMSS - 问题或经验标题

- 页面：datalog
- 类型：坑点 / 排障 / 参数经验 / UI 操作 / 仪器行为
- 现象：
  - ...
- 原因：
  - ...
- 处理办法：
  - ...
- 验证方式：
  - ...
- 风险等级：low / medium / high
```

### 5.3 test_items.md

```markdown
## T-YYYYMMDD-HHMMSS - 测试项名称

- 页面：pmu_dcdc_efficiency
- 目标：说明该测试项验证什么
- 前置条件：
  - ...
- 参数：
  - chip: ...
  - voltage: ...
- 步骤：
  1. ...
- 期望结果：
  - ...
- 数据记录：
  - ...
- 适用范围：
  - ...
```

### 5.4 test_cases.md

```markdown
## TC-YYYYMMDD-HHMMSS - 用例名称

- 页面：kk_serials
- 用例类型：smoke / regression / manual / instrument_required
- 输入：
  - ...
- 执行步骤：
  1. ...
- 期望行为：
  - ...
- 通过标准：
  - ...
- 失败排查：
  - ...
- 可自动化程度：none / partial / full
```

### 5.5 quick_actions.md

```markdown
## QA-YYYYMMDD-HHMMSS - 快捷指令分组名称

- 页面：power_analyser
- 来源：profile_migration / ai_assistant / manual
- 状态：active / draft / deprecated
- 模板：把通道 {ch} 输出电压设到 {v}V
- 占位符：
  - ch: 通道号，例如 1 / 2 / 3 / 4
  - v: 电压值，单位 V
- 适用条件：
  - 当前页面已连接 N6705C
- 执行预期：
  - 触发 AI Assistant 参数填充并调用受控动作
```

## 6. 字段规范

- `页面`：必须填本目录对应的 page_key，且在白名单内。
- `来源`：`profile_migration`（从 profiles.py 迁移）/ `ai_assistant`（AI 沉淀）/ `manual`（人工）。
- `稳定性`（memory 专属）：`stable` 表示已验证可长期依赖；`tentative` 表示待验证，AI 引用须谨慎。
- `状态`（quick_actions 专属）：`active` 生效；`draft` 草稿不展示；`deprecated` 保留历史不再展示。
- `风险等级`（lessons 专属）：`low` / `medium` / `high`，影响 AI 是否主动引用。
- `可自动化程度`（test_cases 专属）：`none` / `partial` / `full`，`full` 条目后续可迁移为 eval case。
- `占位符`（quick_actions 专属）：模板中 `{name}` 形式的参数，UI 侧弹轻量输入框填充后再发送。

## 7. 命名规则

- 文件名固定为 `memory.md` / `lessons.md` / `test_items.md` / `test_cases.md` / `quick_actions.md`，
  本机私有层加 `.local` 后缀（如 `lessons.local.md`）。
- 目录名固定为 page_key，全小写 + 下划线，禁止大写、空格、中文。
- 条目标题用简体中文，简明描述问题或目标，不堆砌关键词。

## 8. 读取策略

- 默认读取 `_shared` + 当前页面目录，不跨页面全量读取。
- 优先注入 `memory.md` 与 `lessons.md` 的最近 / 高稳定条目。
- 页面快捷指令刷新时读取当前页面 `quick_actions.md`，并与本机 `quick_actions.local.md` 合并去重。
- 用户明确问「有没有测试用例 / 常用测试项」时再读取 `test_items.md` 与 `test_cases.md`。
- 单文件读取后先走 `context_budget` 裁剪，避免长文档塞满上下文。

## 9. 安全规则

1. 只能写入 `docs/kk_lab_ai_memory/<page_key>/` 或 `user_data/ai/kk_lab_ai_memory/<page_key>/`。
2. **禁止**写入 `docs/ai/`，该目录仅用于 AI coding 协作、架构说明和需求设计。
3. `page_key` 必须在 §2 白名单中，未知页面写入 `_shared/pending.md` 或拒绝。
4. 写入前执行 `mask_sensitive`，避免 API Key、串口设备唯一标识、内部路径等泄露。
5. 项目级 docs 写入必须弹窗确认；本机私有写入可配置为快速确认。
6. 同一标题 / 高相似内容需要提示重复，避免反复追加垃圾条目。
