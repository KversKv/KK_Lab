# KK Lab AI 记忆体系与测试项归档规划

> 状态：设计稿
> 范围：AI Assistant 在 `docs/` 下沉淀页面级记忆、经验、常用测试项与测试用例的目录体系、写入规则、读取策略与实现计划
> 结论：需求合理，建议先做为「受控文档资产库 + AI 工具写入」能力，而不是让模型直接随意读写项目文件

---

## 0. 需求合理性判断

当前需求是合理的，且与现有 AI Assistant 的定位一致：

| 需求点 | 合理性 | 关键边界 |
|---|---|---|
| 按页面保存记忆、经验、测试项 | 合理。页面是 KK_Lab 中最稳定的业务上下文边界，能避免示波器、串口、电源、PMU 等知识互相污染 | 必须复用现有 `page_key`，避免另造页面命名体系 |
| 让 AI 自动归档到对应文件 | 合理。适合做成受控 Action，不让模型直接任意写文件 | 写入路径必须白名单、内容需脱敏、追加格式需稳定 |
| 让 AI 后续读取这些沉淀 | 合理。可作为 Prompt 动态上下文的一部分按需注入 | 不能全量塞入上下文，需要摘要、检索、预算裁剪 |
| 记录常用测试项与测试用例 | 合理。比纯聊天历史更可复用，可逐步沉淀为 eval / 模板 / quick actions | 测试用例需要结构化字段，不能只堆自由文本 |

建议采用「项目随包沉淀」与「本机私有沉淀」双层设计：
- `docs/kk_lab_ai_memory/`：工具运行期可被 AI Assistant 读取的 KK Lab AI 记忆体系，与 `docs/ai/` 的 AI coding 协作文档隔离。
- `user_data/ai/kk_lab_ai_memory/`：开发态用户本机私有、运行时自动沉淀、默认不纳入版本控制；打包后对应 `%APPDATA%/KK_Lab/ai/kk_lab_ai_memory/`。
- AI Assistant 写入时优先写本机私有层；用户确认有复用价值后再提升为项目级文档。

---

## 1. 目标与非目标

### 1.1 目标

1. 在 `docs/` 中建立页面级归档目录，让不同页面拥有独立的记忆、经验和测试项文件。
2. 在 AI Assistant 中提供「沉淀 / 归档」入口，能根据当前页面自动定位归档文件。
3. 让 Prompt 构建器按当前页面读取相关归档，并在 token 预算内注入上下文。
4. 用统一 Markdown 模板降低后续维护成本，保证 AI 写入内容可读、可 diff、可审查。
5. 为常用测试项保留结构化字段，后续可升级为快捷指令、测试模板或 eval 用例。

### 1.2 非目标

1. 第一版不做向量数据库，不引入 RAG 服务，不新增第三方依赖。
2. 第一版不允许 AI 任意选择文件路径写入，只能写白名单页面目录。
3. 第一版不把所有历史聊天自动保存进 docs，只保存用户显式触发的沉淀内容。
4. 第一版不直接让 AI 修改业务代码或测试流程，只沉淀经验与测试项。

---

## 2. 推荐目录结构

项目级目录建议放在 `docs/kk_lab_ai_memory/`，名称直接表达「KK Lab 的 AI 记忆体系」。目录内部仍按现有页面键划分子目录。`docs/ai/` 只保留本工具开发过程中的 AI coding 协作文档，不承载运行期 AI 记忆：

```text
docs/kk_lab_ai_memory/
├── _shared/
│   ├── README.md
│   ├── conventions.md
│   └── cross_page_lessons.md
├── power_analyser/
│   ├── memory.md
│   ├── lessons.md
│   ├── test_items.md
│   ├── test_cases.md
│   └── quick_actions.md
├── datalog/
│   ├── memory.md
│   ├── lessons.md
│   ├── test_items.md
│   ├── test_cases.md
│   └── quick_actions.md
├── oscilloscope/
├── thermal_chamber/
├── kk_serials/
├── orchestrator/
├── vmin_hunter/
├── consumption_test/
├── pmu_dcdc_efficiency/
├── pmu_output_voltage/
├── pmu_is_gain/
├── pmu_oscp/
├── pmu_gpadc/
├── pmu_clk/
├── charger_config_traverse/
├── charger_status_register/
├── charger_iterm/
└── charger_regulation_voltage/
```

本机私有目录建议镜像同样结构：

```text
user_data/ai/kk_lab_ai_memory/
├── power_analyser/
│   ├── memory.local.md
│   ├── lessons.local.md
│   ├── test_items.local.md
│   ├── test_cases.local.md
│   └── quick_actions.local.md
└── ...
```

### 2.1 页面键来源

页面目录名不新增概念，直接复用 `MainWindow._get_current_help_key()` 返回值：

| 页面 / 子页面 | 目录键 |
|---|---|
| N6705C 电源分析仪 | `power_analyser` |
| N6705C Datalog | `datalog` |
| 示波器 | `oscilloscope` |
| 温箱 | `thermal_chamber` |
| 串口工具 | `kk_serials` |
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

---

## 3. 单页面文件职责

每个页面目录固定 5 个核心文件，第一版只维护这 5 类，避免体系过重：

| 文件 | 记录内容 | AI 读取优先级 | 写入方式 |
|---|---|---|---|
| `memory.md` | 页面长期背景、稳定约定、页面参数含义、常见上下文 | 高 | 人工确认后追加或整理 |
| `lessons.md` | 踩坑、经验、排障结论、异常现象与处理办法 | 高 | AI 沉淀时追加条目 |
| `test_items.md` | 常用测试项、测试前置条件、检查项、人工操作清单 | 中 | AI 归档测试项时追加条目 |
| `test_cases.md` | 结构化测试用例：输入、步骤、期望、判定标准 | 中 | AI 归档测试用例时追加条目 |
| `quick_actions.md` | AI Assistant 页面快捷指令模板，承接现有 `AI_PROFILES[*].quick_actions` | 高 | 迁移已有指令后由 AI 或人工追加 |

`_shared/` 用于跨页面共性内容：
- `conventions.md`：全局写入格式、字段规范、命名规则。
- `cross_page_lessons.md`：跨页面经验，例如仪器连接、日志分析、串口共性问题。

---

## 4. Markdown 写入模板

### 4.1 memory.md

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

### 4.2 lessons.md

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

### 4.3 test_items.md

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

### 4.4 test_cases.md

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

### 4.5 quick_actions.md

现有 `core/ai/profiles.py` 中的 `AI_PROFILES[*].quick_actions` 建议迁移到对应页面目录的 `quick_actions.md`。迁移后，`profiles.py` 只保留页面模型参数与系统提示词，快捷指令作为 KK Lab AI 记忆体系的一部分维护。

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

---

## 5. AI Assistant 集成架构

### 5.1 写入闭环

```text
用户在 AI Assistant 中说「沉淀这条经验 / 归档为测试项」
  → AIService 获取当前 page_key
  → KKLabMemoryCurator 生成结构化草稿
  → 脱敏与重复检测
  → UI 预览草稿，用户确认
  → KKLabMemoryStore 只写入白名单文件
  → 写入结果回显到聊天区
```

建议新增组件：

| 组件 | 放置位置 | 职责 |
|---|---|---|
| `core/ai/kk_lab_memory.py` | core 层 | KK Lab AI 记忆目录映射、白名单路径解析、读写、去重、摘要读取 |
| `core/ai/kk_lab_memory_curator.py` | core 层 | 将对话内容整理为 `memory / lesson / test_item / test_case / quick_action` 草稿 |
| `ui/ai/kk_lab_memory_dialog.py` | UI 层 | 草稿预览、目标类型选择、确认写入 |
| `ActionRegistry` 新动作 | core 层 | `archive_kk_lab_memory`、`search_kk_lab_memory`、`list_kk_lab_memory` |

第一版也可以把 `kk_lab_memory_curator` 合并进现有 `curator.py`，降低文件数量；等能力稳定后再拆分。

### 5.2 读取闭环

```text
页面切换或用户提问
  → PromptManager 获取 page_key
  → KKLabMemoryStore 读取当前页面 + _shared 摘要
  → 按类型和 token 预算裁剪
  → 注入 system/context 段
  → 模型回答时引用页面沉淀
```

读取策略：
- 默认读取 `_shared` + 当前页面目录，不跨页面全量读取。
- 优先注入 `memory.md` 与 `lessons.md` 的最近 / 高稳定条目。
- 页面快捷指令刷新时读取当前页面 `quick_actions.md`，并与本机 `quick_actions.local.md` 合并去重。
- 用户明确问「有没有测试用例 / 常用测试项」时再读取 `test_items.md` 与 `test_cases.md`。
- 单文件读取后先裁剪，避免把长文档塞满上下文。

### 5.3 受控 Action 设计

| Action | 风险 | 功能 |
|---|---|---|
| `archive_kk_lab_memory` | medium | 将当前对话或选中文本归档到当前页面指定文件 |
| `list_kk_lab_memory` | low | 列出当前页面已有记忆条目索引 |
| `search_kk_lab_memory` | low | 在当前页面与 `_shared` 中搜索关键字 |
| `promote_local_kk_lab_memory` | medium | 将本机私有沉淀提升到项目级 docs，需确认 |

安全规则：
1. 只能写入 `docs/kk_lab_ai_memory/<page_key>/` 或 `user_data/ai/kk_lab_ai_memory/<page_key>/`，打包后本机私有层走 `%APPDATA%/KK_Lab/ai/kk_lab_ai_memory/<page_key>/`。
2. 禁止写入 `docs/ai/`，该目录仅用于 AI coding 协作、架构说明和需求设计。
3. `page_key` 必须在白名单中，未知页面写入 `_shared/pending.md` 或拒绝。
4. 写入前执行 `mask_sensitive`，避免 API Key、串口设备唯一标识、内部路径等泄露。
5. 项目级 docs 写入必须弹窗确认；本机私有写入可以配置为快速确认。
6. 同一标题 / 高相似内容需要提示重复，避免反复追加垃圾条目。

---

## 6. 与现有 AI Assist 能力的关系

| 现有能力 | 本方案如何复用 |
|---|---|
| `AIService.set_page_context()` | 继续作为 page_key 来源 |
| `PromptManager` | 增加 KK Lab AI 记忆上下文读取入口 |
| `profiles.py` | 迁移 `AI_PROFILES[*].quick_actions` 到 `docs/kk_lab_ai_memory/<page_key>/quick_actions.md` 后，只保留页面 Profile 与 prompt 参数 |
| `curator.py` | 可复用 AI 草稿润色、规则兜底、脱敏、去重思路，并把快捷指令沉淀目标从 `quick_actions.local.json` 调整为 `quick_actions.local.md` |
| `context_budget.py` | KK Lab AI 记忆注入必须走预算裁剪 |
| `nudges.json` | 继续作为纠偏片段库；快捷指令不再放在 `profiles.py` 或单独 json 中维护 |
| `eval_runner.py` | `test_cases.md` 中可自动化的条目后续迁移为 eval case |

---

## 7. 实现计划

该任务不复杂，建议拆成 3 个阶段，先完成稳定可用的文档归档闭环，再做 UI 体验增强。

### Phase 1：目录规范与手工可用闭环

| 任务 | 产物 | 状态 |
|---|---|---|
| 定义 `docs/kk_lab_ai_memory/` 目录结构与页面键白名单 | 本文档确认的目录规范 | ✅ 已完成 |
| 建立 `_shared` 与重点页面目录模板 | 目录 + 5 类 Markdown 模板文件 | ✅ 已完成 |
| 迁移现有快捷指令到 `quick_actions.md` | 从 `AI_PROFILES[*].quick_actions` 生成页面级快捷指令文档 | ✅ 已完成 |
| 明确每类文件的写入模板与 ID 规则 | `conventions.md` 或模板段落 | ✅ 已完成 |
| 同步 `DIRECTORY_STRUCTURE.txt` | 工程目录说明更新 | ✅ 已完成 |

验收标准：
- 每个页面有固定归档位置。
- 人工可以按模板直接记录经验、测试项和用例。
- 后续 AI 写入不需要再讨论目录命名。

### Phase 2：AI 受控归档与读取

| 任务 | 产物 | 状态 |
|---|---|---|
| 实现 KK Lab AI 记忆路径映射与白名单校验 | `core/ai/kk_lab_memory.py` | ⬜ 未开始 |
| 实现归档草稿生成与脱敏去重 | 复用或扩展 `core/ai/curator.py` | ⬜ 未开始 |
| 增加受控 Action：归档 / 列表 / 搜索 | ActionRegistry 新动作 | ⬜ 未开始 |
| 快捷指令加载改走 KK Lab AI 记忆体系 | `get_quick_actions()` 读取 `quick_actions.md` + `quick_actions.local.md` | ⬜ 未开始 |
| PromptManager 注入 KK Lab AI 记忆摘要 | 当前页面 + `_shared` 预算裁剪读取 | ⬜ 未开始 |
| 增加最小 UI 确认流 | 对话区触发后预览并确认 | ⬜ 未开始 |

验收标准：
- 用户在 AI Assistant 中说「把这条归档为当前页面经验」，AI 能定位当前页面并生成草稿。
- 写入只发生在白名单路径，项目级写入必须确认。
- AI 在当前页面回答时能使用已归档的页面经验。

### Phase 3：测试项复用与维护体验

| 任务 | 产物 | 状态 |
|---|---|---|
| 测试项 / 测试用例条目索引化 | 条目 ID、标题、标签、页面键索引 | ⬜ 未开始 |
| 支持从测试项生成快捷指令草稿 | `quick_actions.md` 草稿或本机 `quick_actions.local.md` 条目 | ⬜ 未开始 |
| 支持可自动化用例导出 eval 草稿 | `tests/ai_eval/cases` 草稿 | ⬜ 未开始 |
| 增加 KK Lab AI 记忆管理入口 | 查看、删除、提升本机经验到项目级 | ⬜ 未开始 |

验收标准：
- 常用测试项能被 AI 检索、复述并转成执行建议。
- 高价值测试用例能被迁移为 eval 或快捷指令。
- KK Lab AI 记忆不会无限膨胀，用户可以维护和清理。

---

## 8. 首批建议落地页面

优先从最常被 AI 辅助的页面开始，不需要一次性填满所有目录：

| 优先级 | 页面 | 原因 |
|---|---|---|
| P0 | `kk_serials` | 日志分析、串口异常、常用命令最适合沉淀 |
| P0 | `datalog` | 波形分析、Datalog 参数、异常判断经验复用价值高 |
| P0 | `orchestrator` | 测试序列、节点配置、脚本草案需要持续沉淀 |
| P1 | `power_analyser` | 通道配置、电压电流设置、仪器行为经验明确 |
| P1 | PMU / Charger 子页面 | 测试项稳定后可形成测试用例库 |
| P2 | `oscilloscope` / `thermal_chamber` / `vmin_hunter` | 按使用频率逐步补齐 |

---

## 9. 风险与对策

| 风险 | 表现 | 对策 |
|---|---|---|
| 文档越写越乱 | 重复条目、标题不统一、长段聊天粘贴 | 固定模板 + 去重 + 用户确认 |
| 上下文膨胀 | KK Lab AI 记忆太多导致模型输入过长 | 摘要读取 + token 预算 + 按需读取 test cases |
| 错误经验被固化 | AI 误总结后进入长期记忆 | 默认草稿预览确认，条目标记 `tentative/stable` |
| 敏感信息入库 | API Key、内部路径、设备唯一标识进入 docs | 写入前统一脱敏，项目级写入二次确认 |
| 页面键漂移 | 页面目录与 profile/help key 不一致 | 以 `_get_current_help_key()` 为唯一页面键来源 |

---

## 10. 推荐结论

建议推进该体系，但第一版保持轻量：

1. 先建立 `docs/kk_lab_ai_memory/` 的 KK Lab AI 记忆归档规范，并明确禁止运行期记忆写入 `docs/ai/`。
2. 先支持「用户显式要求沉淀」的受控写入，不做全自动聊天记录入库。
3. 先让 AI 读取当前页面与 `_shared` 的摘要，不做跨库检索和向量化。
4. 待常用测试项稳定后，再把高价值条目提升为 quick actions、eval cases 或测试模板。

这样既能满足「沉淀和记录常用测试项」的需求，又不会引入过重架构或让 AI 文件写入失控。
