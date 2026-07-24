# ui/pages/orchestrator — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **编排引擎（core）** → @see [core/orchestrator/](../../../core/orchestrator/)（compiler / executor / nodes / document / serialization）
- **分层架构** → @see [docs/ai/04_ARCHITECTURE.md](../../../docs/ai/04_ARCHITECTURE.md)
- **用户手册** → `docs/User Manual/ORCHESTRATION/Orchestrator.md`

## 本模块职责与边界

- **职责**：可视化自定义测试序列编辑器（三栏：节点面板 / 画布 / 属性）。
- **上游**：`ui/main_window.py`；**下游**：`core/orchestrator/` 引擎、`core/instruments/InstrumentManager`。
- **铁律**：UI 节点（`ui/pages/orchestrator/nodes/`）是**视图层**；节点执行逻辑在 `core/orchestrator/nodes/`（无 QtWidgets）。

## 接口契约（对外不可破坏）

- `ExecutorThread`（core）：QtCore 信号驱动，无 QtWidgets；UI 经 Signal/Slot 订阅执行进度 / 事件。
- `SequenceCanvas` / `NodePalette` / `PropertyPanel` 三栏经 `OrchestratorDocument v3`（metadata/view_state/dirty/source_path）同步。
- 序列读写走 `core/orchestrator/serialization`（v2 迁移）；模板 / 最近序列路径走 `core/orchestrator/paths`。

## 局部约定

- 新增节点：`core/orchestrator/nodes/` 加 `BaseNode` 子类并注册 `NODE_REGISTRY`；UI 侧 `nodes/` 加对应视图 + `node_metadata`。
- 仪器节点 capability 经 `InstrumentResolver` 解析 adapter / lease，不直接持仪器。
- 运行产物（manifest / snapshot / report / logs）经 `RunHistoryWriter` 落 run folder。

## 局部坑点

- UI 节点与 core 节点**勿混层**；视图画布操作不直接发 SCPI。
- SVG 图标渲染禁 `setDevicePixelRatio`（见 03§23）。
- 断点 / 单步经 `breakpoints.py` 的 `BreakpointSet / StepRunState`。
