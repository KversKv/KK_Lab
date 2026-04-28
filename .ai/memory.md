# KK_Lab - AI 长期记忆（Session Memory）

> 本文件用于 AI 在不同会话之间**沉淀项目关键上下文**。
> 写入规则：
> - 只记录**长期有效**的信息（约定、决策、踩过的坑、固定的偏好）；
> - 临时调试步骤 / 一次性任务 **不要**写进来；
> - 保持每条精炼（1-3 行）。

---

## 项目核心

- 项目：**KK_Lab** — PySide6 桌面工具，BES 芯片功耗 / PMU / Charger 测试。
- 平台：Windows 64-bit；Python ≥ 3.10；PowerShell 开发环境。
- 入口文档：[CLAUDE.md](../CLAUDE.md) → [docs/ai/](../docs/ai/)。
- 任务 SOP：[docs/ai/09_WORKFLOW.md](../docs/ai/09_WORKFLOW.md)（调用 / 执行 / 回归三阶段）。

## 必守铁律

1. 禁 `print`，统一 `log_config.get_logger`。
2. `instruments/` 不依赖 Qt；UI 不直调 VISA。
3. 仪器创建统一走 `instruments/factory.py`。
4. 新仪器必须同步 Mock（`instruments/mock/mock_instruments.py`）。
5. `DEBUG_MOCK` 改完需重启应用；不得热切换。
6. 跨线程只用 Signal/Slot。
7. 结果写 `Results/`，文件名带时间戳。
8. 未经用户许可不 `git commit`、不主动新建 `*.md`。
9. 工程清单同步矩阵（[project-rules.md §8](../.trae/rules/project-rules.md)）必遵守：改目录 → `DIRECTORY_STRUCTURE.txt`；改运行时资源 → `spec/kk_lab.spec`；新功能页 → `helps/`；新 import → `requirements.txt`。

## 打包

- 主程序：`python -m PyInstaller spec/kk_lab.spec --clean --noconfirm`
- 子工具：`python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm`
- 资源路径：`sys._MEIPASS` fallback 到脚本目录。

## 常见坑（高优先级提醒）

- `sys.stdout / stderr` 在打包 `windowed` 下为 None，入口已兜底。
- `pyvisa.ResourceManager.__del__` 退出崩溃，入口已 patch，勿删。
- QPainter 警告已过滤。
- `HoverFixStyle` 用于 Fusion 风格 `:hover` 生效，勿替换。

## 会话决策 / 偏好

- 回复语言：**简体中文**（随用户语言切换）。
- 代码注释：**不主动增删**，保留原文件风格。
- 新文档模板：沿用 `docs/ai/00_OVERVIEW.md` ~ `08_CHECKLISTS.md` 的编号与结构。

## 变更履历

| 日期 | 变更 | 备注 |
|---|---|---|
| 2026-04-28 | 建立 AI 协作文档体系（`docs/ai/`、`AGENTS.md`、`.trae/rules/`、`.ai/memory.md`） | 根据用户请求初始化 |
| 2026-04-28 | 新增 [docs/ai/09_WORKFLOW.md](../docs/ai/09_WORKFLOW.md)，落盘任务 SOP；CLAUDE.md / AGENTS.md / project-rules.md / 00_OVERVIEW.md 已同步引用 | 明确"调用 / 执行 / 回归"三阶段流程 |
| 2026-04-28 | 增补"工程清单同步矩阵"硬规则至 [project-rules.md §8](../.trae/rules/project-rules.md)、[08_CHECKLISTS.md](../docs/ai/08_CHECKLISTS.md) 通用勾项、[09_WORKFLOW.md §3.5.1](../docs/ai/09_WORKFLOW.md) | 封堵 `DIRECTORY_STRUCTURE.txt` / `requirements.txt` 盲区 |
