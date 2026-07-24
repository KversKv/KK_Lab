# User Manual 更新历史

本文件记录 `docs/User Manual/` 目录下用户手册的每次更新：时间、git 节点、变更范围与摘要。

> 维护规则：
> - 每次新增 / 修改 / 删除本目录下任何 `.md` 文件，须在本文件**顶部追加**一条记录（最新在上）。
> - 记录字段固定为：`日期` / `git commit` / `分支` / `操作类型` / `变更范围` / `摘要`。
> - git 节点取**本次更新开始时**的工作区 HEAD；若更新未提交，标注 `(uncommitted)`。
> - 摘要须列出本次实际改动的文件清单与一句话目的，不要复述全文。

---

## 2026-07-18

| 字段 | 值 |
|---|---|
| 日期 | 2026-07-18 |
| git commit | `daffb64b53b8a76ff124f216bf7941cd7f7090df`（短哈希 `daffb64`） |
| 分支 | `main` |
| 操作类型 | 新建 |
| 变更范围 | `docs/User Manual/` 全目录（31 个 md 文件） |

### 摘要

按 `ui/main_window.py` 主窗口导航结构首次建立完整的用户手册目录，覆盖 INSTRUMENTS / AUTOMATION / TOOLS / ORCHESTRATION 四个分组下的全部页面与子页面。每份手册统一含 6 章节：页面入口、界面布局、典型操作流程、关键参数说明、注意事项、跨页引用。

**新增文件清单**

- `README.md` — 总入口（启动说明 + 页面索引 + 通用约定）
- `INSTRUMENTS/N6705C Power Analyzer/README.md` — N6705C 子页面索引
- `INSTRUMENTS/N6705C Power Analyzer/N6705C Analyser.md` — 电源分析仪实时控制台
- `INSTRUMENTS/N6705C Power Analyzer/N6705C Datalog.md` — 数据采集与波形分析
- `INSTRUMENTS/Oscilloscope.md` — 示波器控制（MSO64B / DSOX4034A）
- `INSTRUMENTS/Chamber.md` — 温箱控制（VT6002 等）
- `AUTOMATION/PMU Test/README.md` + 6 子页：`DCDC Efficiency.md` / `Output Voltage.md` / `Is_gain.md` / `OSCP.md` / `GPADC Test.md` / `CLK Test.md`
- `AUTOMATION/Charger Test/README.md` + 4 子页：`Config Traverse Test.md` / `Status Register Test.md` / `Iterm Test.md` / `Regulation Voltage Test.md`
- `AUTOMATION/Module Test/README.md` + 2 子页：`LDO.md` / `DCDC.md`
- `AUTOMATION/Consumption Test/README.md` + 2 子页：`Auto Test.md` / `High-Low Temperature Test.md`
- `AUTOMATION/VminHunter.md` — Vmin 探底测试
- `TOOLS/PMU/README.md` + 2 子页：`1811.md` / `1860.md`（1860 为占位）
- `TOOLS/Collection/README.md` + 3 子页：`MCU IO.md` / `KK Serials.md` / `IIC Control.md`
- `ORCHESTRATION/Orchestrator.md` — 节点式测试序列编辑器
- `history.md` — 本文件

### 内容来源依据

- 页面结构：`ui/main_window.py::_create_main_content` + `ui/nav_controller.py::create_left_nav` / `create_submenus`
- 子页面切换：`nav_controller` 的 `pmu_test_tab_map` / `charger_test_tab_map` / `consumption_test_tab_map` / `module_test_tab_map` / `collection_submenu` / `pmu_tool_submenu` / `pa_submenu`
- 每页源码：`ui/pages/<page>/` 下对应 UI 文件
- 已有内部文档复用：`ui/pages/pmu/pmu_1811/README.md`、`ui/pages/n6705c_power_analyzer/n6705c_datalog_ui_usage.md`、`docs/user/IIC_Module/`、`docs/ai/VminHunter/`
- 项目红线：`AGENTS.md` + `.trae/rules/project-rules.md`（不硬编码地址、I2C 即用即销、统一日志、QSplitter 配 ExecutionLogsFrame 等）
