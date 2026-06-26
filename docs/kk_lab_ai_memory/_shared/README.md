# KK Lab AI 记忆体系

> 范围：AI Assistant 在 `docs/kk_lab_ai_memory/` 下沉淀的页面级记忆、经验、常用测试项与测试用例。
> 定位：受控文档资产库，由 AI Assistant 经白名单受控写入，或人工按模板直接维护。
> 规划来源：[AIAssist_KKLabAIMemoryArchivePlan.md](../ai/feature_requests/AIAssist/AIAssist_KKLabAIMemoryArchivePlan.md)

---

## 1. 与 `docs/ai/` 的边界

- `docs/ai/` 仅用于 AI coding 协作、架构说明和需求设计，**禁止**承载运行期 AI 记忆。
- `docs/kk_lab_ai_memory/` 承载 AI Assistant 运行期沉淀的页面经验、测试项与测试用例。
- 本机私有沉淀镜像在 `user_data/ai/kk_lab_ai_memory/<page_key>/*.local.md`，打包后对应
  `%APPDATA%/KK_Lab/ai/kk_lab_ai_memory/<page_key>/`，默认不纳入版本控制。

## 2. 目录结构

```text
docs/kk_lab_ai_memory/          # 目录结构按左侧导航栏 4 大组归类
├── _shared/
│   ├── README.md              # 本文件：体系总览
│   ├── conventions.md         # 写入规范、模板、ID 规则、字段规范、白名单
│   └── cross_page_lessons.md  # 跨页面共性经验
├── instrument/                # 导航 INSTRUMENTS
│   ├── power_analyser/        # N6705C 簇伞目录（总记忆）
│   │   ├── power_analyser/    # page_key=power_analyser
│   │   └── datalog/           # page_key=datalog
│   ├── oscilloscope/          # page_key=oscilloscope
│   └── thermal_chamber/       # page_key=thermal_chamber
├── automation/                # 导航 AUTOMATION
│   ├── pmu_test/              # PMU 簇伞目录（总记忆：通用测试项 + 跨芯片差异 + 共性经验）
│   │   ├── memory.md / lessons.md / test_items.md / test_cases.md / quick_actions.md
│   │   ├── pmu_dcdc_efficiency/  # page_key=pmu_dcdc_efficiency
│   │   ├── pmu_output_voltage/
│   │   ├── pmu_is_gain/
│   │   ├── pmu_oscp/
│   │   ├── pmu_gpadc/
│   │   └── pmu_clk/
│   ├── charger_test/          # Charger 簇伞目录（总记忆）
│   │   ├── charger_config_traverse/  # page_key=charger_config_traverse
│   │   ├── charger_status_register/
│   │   ├── charger_iterm/
│   │   └── charger_regulation_voltage/
│   ├── consumption_test/      # page_key=consumption_test
│   └── vmin_hunter/           # page_key=vmin_hunter
├── tools/                     # 导航 TOOLS
│   ├── kk_serials/            # page_key=kk_serials
│   └── collection/            # page_key=collection
└── orchestration/             # 导航 ORCHESTRATION
    └── orchestrator/          # page_key=orchestrator（每个页面目录固定 5 个核心文件）
```

> 伞目录（umbrella）概念见 [conventions.md §2.1](./conventions.md#21-伞目录键umbrella)：
> 承载跨页面的同一业务簇总记忆（如 `automation/pmu_test`、`automation/charger_test`、
> `instrument/power_analyser`）。所有页面记忆目录按左侧导航 4 大组（INSTRUMENTS /
> AUTOMATION / TOOLS / ORCHESTRATION）物理归入对应一级父目录，page_key
> 对外不变（详见 §2.1 物理目录归类）。

## 3. 页面键来源

页面目录名**唯一来源**是 `MainWindow._get_current_help_key()`，不另造命名体系。
完整白名单与页面键映射见 [conventions.md](./conventions.md) §2。

## 4. 单页面文件职责

| 文件 | 记录内容 | AI 读取优先级 | 写入方式 |
|---|---|---|---|
| `memory.md` | 页面长期背景、稳定约定、参数含义 | 高 | 人工确认后追加或整理 |
| `lessons.md` | 踩坑、经验、排障结论、异常处理 | 高 | AI 沉淀时追加条目 |
| `test_items.md` | 常用测试项、前置条件、检查项 | 中 | AI 归档测试项时追加 |
| `test_cases.md` | 结构化用例：输入、步骤、期望、判定 | 中 | AI 归档用例时追加 |
| `quick_actions.md` | AI Assistant 快捷指令模板 | 高 | 迁移已有指令后由 AI/人工追加 |

## 5. 写入与读取规则摘要

- **写入**：只能写白名单页面目录；项目级 `docs/` 写入必须弹窗确认；本机私有层可快速确认。
- **读取**：默认读取 `_shared` + 当前页面目录，不跨页面全量读取；优先注入 `memory.md` 与
  `lessons.md` 的高稳定条目；`test_items.md` / `test_cases.md` 按需读取。
- **脱敏**：写入前统一 `mask_sensitive`，避免 API Key、串口设备唯一标识、内部路径泄露。
- **去重**：同一标题 / 高相似内容需提示重复，避免反复追加垃圾条目。

详细规范见 [conventions.md](./conventions.md)。
