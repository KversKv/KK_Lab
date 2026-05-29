# Custom Test 优化方案（适配当前项目结构）

> 适用版本：截至 2026-05-29 的 `KK_Lab` 当前实现。  
> 关联文档：`docs/user/CustomTestStructure.md`。  
> 本文是优化路线文档，不代表已经开始代码改造。

## 0. 结论摘要

当前 Custom Test 的优化方向整体是合理的，但需要按当前项目结构重新校准优先级。

原方案中最值得保留的判断是：

- 保留树形可视化测试序列编辑器，不改成自由连线节点图。
- 继续使用版本化 JSON DSL 保存序列和模板。
- 继续强化 `PARAM_SCHEMA`、preflight、ResultStore、仪器 adapter、manifest 和 run history。
- 通过执行快照、运行期间只读、timeout/cancel、sequence hash 提升长时间测试稳定性和可追溯性。
- UI 体验优先补齐搜索、模板库、复制粘贴、运行状态、结果图表配置等工程效率能力。

需要修正的地方是：

- `core/custom_test/` 已经存在，执行器、上下文、节点、校验、序列化、结果模型和 resolver 已经迁移到 core 层；后续不是“从 UI 迁移到 core”，而是在现有 core 基础上继续收敛边界。
- `ui/pages/custom_test/executor.py`、`context.py`、`nodes/*` 当前主要是兼容 shim，不应再把它们当作主实现。
- `SequenceDocument` 已在 `core/custom_test/serialization.py` 中存在，但它仍是轻量加载结果，不是完整文档模型；后续可以扩展为 v3 文档模型。
- 表达式求值已经使用受限 AST，不是直接 `eval`；优化重点应从“替换 eval”调整为“扩展白名单、补齐语法校验和错误提示”。
- `PromptUser` 已通过 `CustomTestUI._request_user_prompt()` 接入 UI 对话框，原方案中“缺接收端”的问题已经不再成立。
- 模板加载已经通过 `load_sequence_file()` 统一处理 list/dict 序列格式，原方案中“内置 dict 模板无法通过 template 入口加载”的问题已经不再成立。

综合判断：该 Optimize 方案合理，推荐按“安全加固优先、体验增强其次、架构大替换最后”的节奏推进。不要一开始就大规模重命名 UI 文件或替换 `QTreeWidget`，这样风险高、收益滞后。

## 1. 当前基线

当前 Custom Test 已经形成较清晰的 UI/core 分层。

```text
ui/pages/custom_test/
├── custom_test_ui.py              # 页面装配、运行编排、Prompt、自动导出
├── node_palette.py                # 左侧节点库
├── sequence_canvas.py             # 基于 QTreeWidget 的序列画布
├── property_panel.py              # PARAM_SCHEMA 驱动的属性表单
├── record_data_editor.py          # RecordDataPoint 专属字段编辑器
├── instrument_connection_panel.py # 仪器连接区域
├── result_panel.py                # Logs/Data/Chart
├── validation_panel.py            # preflight issues 对话框
├── node_metadata.py               # 节点可见性/状态元数据
├── sequence_io.py                 # 兼容 shim，委托 core serialization
├── executor.py                    # 兼容 shim
├── context.py                     # 兼容 shim
└── nodes/                         # 兼容 shim

userdata/custom_test_templates/     # Custom Test 模板目录，不放在 UI 包内

core/custom_test/
├── nodes/
│   ├── base.py                    # BaseNode、NODE_REGISTRY、clone/to_dict/from_dict
│   ├── instrument_nodes.py        # N6705C/Scope/Chamber/I2C/MCU/UART/RF 预留
│   ├── logic_nodes.py             # Loop/If/Delay/变量/Prompt/PassFail 等
│   ├── io_nodes.py                # RecordData/ExportResult/PrintLog
│   └── value_nodes.py             # 常量、增减、列表、类型转换、统计等
├── serialization.py               # list/v1/v2 兼容加载、迁移、保存
├── validation.py                  # preflight 参数/变量/仪器校验
├── resolver.py                    # capability 到 runtime adapter 的解析
├── context.py                     # 变量、结果、暂停/停止、Prompt、资源释放
├── runtime.py                     # execute_node / execute_children
├── executor.py                    # CustomTestExecutor / ExecutorThread
├── result_store.py                # records、field meta、CSV/XLSX、manifest
└── adapters/
    ├── base.py                    # adapter 基础定义
    └── mock.py                    # mock adapter
```

运行时核心链路：

```text
CustomTestUI._on_run()
    -> canvas.get_sequence()
    -> InstrumentResolver
    -> preflight_validate()
    -> ExecutionContext
    -> acquire_leases()
    -> ExecutorThread.start(sequence, context)
    -> CustomTestExecutor.run()
    -> execute_node() / execute_children()
    -> ResultStore
    -> ResultPanel + CSV/XLSX manifest
```

## 2. 优化原则

### 2.1 不推翻当前结构

当前结构已经把核心执行逻辑放到 `core/custom_test/`。后续应优先在现有模块上增量增强，避免为了“看起来更分层”而把已经稳定的文件大规模重命名。

推荐：

```text
先增强现有 core/custom_test 模块
再逐步抽出 snapshot/schema/symbols/events/report 等新模块
最后才考虑 UI views/controllers 目录拆分
```

暂不推荐：

```text
一次性把 custom_test_ui.py 拆成多个 controller
一次性用 QAbstractItemModel 替换 QTreeWidget
一次性引入完整 workflow engine
一次性改成自由连线式节点图
```

### 2.2 UI 只做编辑、展示和运行编排

符合项目分层铁律：

```text
main.py -> ui/ <-> core/ -> instruments/ -> lib/
```

Custom Test 中应继续保持：

- UI 不直接做阻塞仪器 IO。
- UI 不写测试逻辑。
- core 不依赖 Qt Widget。
- instruments 不依赖 UI。
- 仪器创建和占用优先走 `InstrumentManager`、factory、resolver、adapter。

### 2.3 兼容优先

仓库中已有内置模板和用户序列。优化时必须保持兼容：

- legacy list 格式。
- v1/v2 dict 格式。
- 当前 `BaseNode.to_dict()` / `from_dict()`。
- 当前 `ui/pages/custom_test/*` 兼容 shim。
- 当前 `PARAM_SCHEMA` 的 dict 写法。
- 模板目标目录为 `userdata/custom_test_templates/`，不再放入 `ui/pages/custom_test/`。

## 3. 目标结构建议

短期目标不是重排所有目录，而是在现有结构中补齐缺失模块。

### 3.1 建议新增或增强的 core 模块

```text
core/custom_test/
├── snapshot.py        # 运行快照、canonical JSON、sequence hash
├── schema.py          # ParamDef/OutputDef 辅助类型，兼容现有 dict schema
├── symbols.py         # VariableSymbolTable，变量来源、类型、作用域
├── compiler.py        # P2：ExecutionPlan 编译
├── execution_plan.py  # P2：ExecutionPlan / ExecutionStep 数据结构
├── events.py          # P2：ExecutionEvent 统一事件模型
├── reports.py         # P2：HTML 报告生成
└── history.py         # P2：run folder / manifest / events.jsonl 管理
```

注意：`document.py` 可以作为 P1/P2 引入，但当前 `serialization.py` 已有轻量 `SequenceDocument`。如果新增 `document.py`，需要明确职责：

- `serialization.SequenceDocument`：兼容加载结果。
- `document.SequenceDocument`：完整可编辑文档模型，包含 metadata、view_state、dirty state、source path。

如果不想出现同名混淆，也可以把完整模型命名为 `CustomTestDocument`。

### 3.2 UI 目录拆分建议

当前 UI 文件还没有大到必须立刻重排目录。推荐先保持现状，后续在功能变多时再拆。

可选长期形态：

```text
ui/pages/custom_test/
├── custom_test_ui.py          # 顶层页面壳，保留现有入口名
├── controllers/               # P2/P3，再引入
│   ├── sequence_controller.py
│   ├── run_controller.py
│   ├── result_controller.py
│   └── instrument_controller.py
├── views/                     # P2/P3，再从现有文件渐进迁出
│   ├── palette_view.py
│   ├── sequence_view.py
│   ├── property_view.py
│   ├── result_view.py
│   ├── template_gallery.py
│   └── validation_dialog.py

userdata/custom_test_templates/
└── *.json                     # 项目/用户可维护的 Custom Test 模板
```

更稳妥的顺序是：先在原文件中补功能，等行为稳定且测试覆盖足够后，再按职责搬迁。

## 4. 分阶段路线

### Phase 0：先做低风险校准

目标：让 OP 方案和当前代码一致，避免后续按过时信息实施。

任务：

1. 以 `core/custom_test/` 为执行内核唯一事实源。
2. 保留 `ui/pages/custom_test/*` shim，不主动删除。
3. 文档和代码注释统一说明 v2 当前序列格式。
4. 将模板目录约定为 `userdata/custom_test_templates/`，UI 目录不再承载模板数据。
5. 检查模板是否都能通过 `load_sequence_file()` 读取。
6. 检查 RF Analyzer 等未接入节点在 palette、preflight、文档中的状态一致。

验收：

- 所有模板加载入口行为一致。
- 文档中不再描述已经迁移完成的旧架构。
- 未支持节点不会被误认为可正常运行。

### Phase 1：运行安全和追溯优先

目标：优先降低长时间自动化测试中的运行一致性风险。

#### 1. 运行快照

当前 `_on_run()` 直接使用 `canvas.get_sequence()` 返回的节点对象。建议新增快照函数：

```python
def clone_sequence(nodes: list[BaseNode]) -> list[BaseNode]:
    return [node.clone() for node in nodes]
```

更完整版本放入：

```text
core/custom_test/snapshot.py
```

Run 流程调整为：

```text
editor_nodes = canvas.get_sequence()
snapshot = clone_sequence(editor_nodes)
preflight_validate(snapshot, resolver)
ExecutorThread.start(snapshot, context)
```

快照要求：

- 不引用 `QTreeWidgetItem`。
- 不共享 UI 正在编辑的 node 实例。
- 包含稳定 `uid`、`node_type`、`params`、`children`。
- 用同一份 snapshot 计算 sequence hash、preflight、执行和导出。

#### 2. 运行期间只读

当前 `SequenceCanvas.set_running_state(True)` 已有运行态，但需要进一步确认覆盖所有入口：

- Add/Remove/Move/Load/Save/Template 禁用。
- 拖拽禁用。
- 右侧属性面板只读。
- RecordData 专属编辑器只读。
- Instrument connection 修改入口禁用或延后生效。
- 结果面板仍允许查看、排序、导出当前 view。

#### 3. sequence hash 和 manifest

`ResultStore.build_manifest()` 已支持 `sequence_hash` 参数，但当前自动导出没有传入。建议在 `snapshot.py` 中增加：

```text
canonical_sequence_json(nodes)
build_sequence_hash(nodes)
```

hash 规则：

- 保留 `node_type`、`uid`、`params`、`children`。
- 不包含 UI view state。
- key 稳定排序。
- 使用 UTF-8 JSON 计算 SHA256。

manifest 建议逐步补齐：

```json
{
  "run_id": "...",
  "sequence_hash": "...",
  "sequence_name": "...",
  "sequence_file": "...",
  "start_time": "...",
  "end_time": "...",
  "duration_s": 0,
  "status": "passed|failed|stopped",
  "instrument_snapshot": {},
  "row_count": 0,
  "field_metadata": []
}
```

#### 4. timeout/cancel 审计

当前 `ExecutionContext.sleep()` 已经支持 stop/pause 轮询，但仪器 IO 的停止响应仍取决于具体 adapter/driver。建议先做审计表，再逐项改造。

优先检查：

- VISA timeout 是否设置。
- Serial read 是否有 timeout。
- I2C 操作是否可能无限等待。
- Chamber wait 是否分段 sleep 并检查 stop。
- Scope acquisition/measure 是否有超时。
- UART receive 是否禁止无限阻塞。

短期不一定要马上引入完整 `CancelToken` 类，可以先统一约定：

```python
adapter.method(..., timeout_s=5.0)
context.check_stop()  # 如果后续新增
context.sleep(..., poll=0.1)
```

当 adapter 数量继续增加时，再升级为：

```text
core/custom_test/cancel.py
```

#### 5. preflight 和参数即时校验

`validation.py` 已经检查空序列、部分参数、变量引用、表达式语法和仪器 capability。下一步应增强：

- 根据 `PARAM_SCHEMA` 自动检查 required/type/min/max/options。
- 属性面板编辑时即时提示错误。
- 表达式错误定位到字段。
- 分支变量、循环变量、RecordData 字段引用更准确。
- 对 unsupported 节点给出更明确的修复建议。

### Phase 2：工程效率和 UI 体验

目标：让用户更快搭建、复用和调试测试序列。

优先级建议：

1. Palette 搜索。
2. 空状态引导。
3. Template Gallery。
4. Recent Sequences。
5. Copy / Paste / Duplicate。
6. Delete / Move Up / Move Down 快捷键完善。
7. Step 状态列和 duration。
8. Run Summary。
9. Chart 字段选择和配置保存。

这些功能大多可以先在现有 `NodePalette`、`SequenceCanvas`、`PropertyPanel`、`ResultPanel` 上增量实现，不需要先切换到 `QAbstractItemModel`。

UI 体验原则：

- Custom Test 是工程工具，不应做成营销式页面。
- 信息密度要适中，适合长时间看日志、表格、状态。
- 节点搜索、模板、结果图表要服务真实测试效率。
- 运行状态应清楚，但不要用过度动画干扰测试观察。
- 所有长任务继续放在线程或 core 层，UI 只接收 signal。

### Phase 3：文档模型和编辑器能力

目标：从“节点树 + 序列化工具”升级为真正的 Custom Test 文档模型。

建议新增完整文档模型：

```python
@dataclass
class CustomTestDocument:
    version: int
    sequence: list[BaseNode]
    instruments: dict
    metadata: dict
    view_state: dict
    source_path: str | None = None
    dirty: bool = False
```

v3 保存格式建议：

```json
{
  "version": 3,
  "metadata": {
    "name": "Power vs Temperature Test",
    "description": "",
    "author": "",
    "created_at": "",
    "modified_at": "",
    "required_capabilities": [],
    "tags": []
  },
  "sequence": [],
  "instruments": {},
  "view_state": {
    "expanded_nodes": [],
    "selected_node_uid": null,
    "splitter_sizes": [],
    "chart_config": {}
  }
}
```

迁移规则：

- list -> v3。
- v1/v2 dict -> v3。
- 缺失参数继续使用当前节点默认值。
- 未知节点保留 issue，不应让整个文件静默失败。

编辑器能力：

- Command Pattern。
- Undo / Redo。
- Copy / Paste。
- Duplicate。
- Dirty state。
- 保存前校验。

`QAbstractItemModel + QTreeView` 是长期方向，但建议放到 P2/P3 后期。当前 `QTreeWidget` 已承载较多交互，直接替换风险较高。

### Phase 4：执行可观测性和结果产品化

目标：让测试运行可记录、可回放、可对比、可报告化。

建议逐步加入：

- `ExecutionEvent` 内部事件模型。
- `events.jsonl`。
- run folder。
- `sequence_snapshot.json`。
- `manifest.json`。
- `results.csv` / `results.xlsx`。
- chart PNG。
- HTML report。

推荐 run folder：

```text
Results/custom_test/<run_id>/
├── manifest.json
├── sequence_snapshot.json
├── results.csv
├── results.xlsx
├── events.jsonl
├── logs.txt
├── charts/
│   └── chart.png
└── report.html
```

先做 HTML 报告，再考虑 PDF。PDF 往往涉及字体、分页、打包依赖，适合放后面。

### Phase 5：长期架构能力

这些能力合理，但不建议早期抢做：

- ExecutionPlan 编译。
- Dry Run。
- Breakpoint / Step Run。
- Run to selected。
- 子序列 / Macro。
- 批量参数 Sweep 专用模型。
- 远程执行或无 UI 执行入口。

这些能力依赖前面的 snapshot、symbols、events、history 和 schema。基础没稳之前引入，容易让执行链路复杂化。

## 5. 优先级清单

### P0：近期必须优先做

| 改进项 | 落点 | 原因 |
|---|---|---|
| Run 使用 deep-copied snapshot | `core/custom_test/snapshot.py`, `custom_test_ui.py` | 防止运行中 UI 编辑影响执行 |
| 运行期间完全只读 | `sequence_canvas.py`, `property_panel.py`, `custom_test_ui.py` | 保证执行一致性 |
| sequence hash 写入 manifest | `snapshot.py`, `result_store.py`, `custom_test_ui.py`, `io_nodes.py` | 结果可追溯 |
| timeout/cancel 审计 | `core/custom_test/nodes/*`, `adapters/*`, instrument drivers | 防止 Stop 被长 IO 卡住 |
| `PARAM_SCHEMA` 自动校验 | `validation.py`, `property_panel.py` | 降低运行时失败 |
| unsupported 节点状态收敛 | `node_metadata.py`, `validation.py`, `instrument_nodes.py` | 避免用户误用未接入能力 |

### P1：强烈建议做

| 改进项 | 落点 | 原因 |
|---|---|---|
| Palette 搜索 | `node_palette.py` | 节点数量已多，查找成本会上升 |
| Template Gallery | `custom_test_ui.py`, 新 UI 对话框 | 提升复用和入门效率 |
| Copy/Paste/Duplicate | `sequence_canvas.py` | 提高复杂序列编辑效率 |
| Step 状态列和 duration | `sequence_canvas.py`, `executor.py` | 运行过程更可观察 |
| Run Summary | `custom_test_ui.py`, `validation_panel.py` | 运行前确认仪器、循环、导出路径 |
| Chart 字段配置 | `result_panel.py`, v3 `view_state` | 支撑真实数据分析 |

### P2：产品化增强

| 改进项 | 落点 | 原因 |
|---|---|---|
| 完整 `CustomTestDocument` | `core/custom_test/document.py` | 统一 metadata、view_state、dirty state |
| v3 迁移 | `serialization.py`, `document.py` | 支持长期格式演进 |
| Command Pattern + Undo/Redo | `sequence_canvas.py`, 可新增 controller | 编辑器基本能力 |
| Run History | `history.py`, `result_store.py` | 测试记录可追溯 |
| HTML Report | `reports.py` | 交付和复查更方便 |
| ExecutionEvent | `events.py`, `executor.py` | 统一日志、状态、结果和历史 |

### P3：长期架构升级

| 改进项 | 备注 |
|---|---|
| QAbstractItemModel 替换 QTreeWidget | 等 Command/Document 稳定后再做 |
| ExecutionPlan 编译执行 | 等 snapshot/schema/symbols 稳定后再做 |
| Dry Run | 依赖 ExecutionPlan 和 resolver mock 能力 |
| Breakpoint / Step Run | 依赖事件流和 step state |
| Sub-sequence / Macro | 依赖文档模型和序列引用规范 |

## 6. 对原方案的逐项合理性判断

| 原建议 | 判断 | 调整意见 |
|---|---|---|
| 保留树形序列编辑器 | 合理 | 继续坚持，这是测试流程最合适的形态 |
| 使用版本化 JSON DSL | 合理 | 当前 v2 已存在，v3 应保留兼容迁移 |
| UI/core 分层 | 合理且已部分完成 | 不再做“大迁移”，改为补齐边界和 shim 策略 |
| 运行快照 | 很合理 | P0，当前仍需要做 |
| 表达式安全化 | 方向合理但描述需更新 | 已有受限 AST，后续增强白名单和提示 |
| 所有 IO timeout/cancel | 很合理 | P0，但应先审计再逐步改 adapter/driver |
| SequenceDocument | 合理 | 当前已有轻量对象，完整文档模型放 P2 |
| SequenceModel/QAbstractItemModel | 合理但不急 | P3，直接替换风险高 |
| Command Pattern/Undo Redo | 合理 | P2，先做 Copy/Paste/Duplicate 更快见效 |
| VariableSymbolTable | 合理 | P1/P2，可先服务 preflight 和 RecordData |
| Template Gallery | 合理 | P1，用户价值高 |
| Palette 搜索 | 很合理 | P1，节点数量已足够需要搜索 |
| Step 状态列 | 很合理 | P1，运行可观察性明显提升 |
| ExecutionEvent | 合理但不急 | P2，先不要替换现有 Qt signals |
| ExecutionPlan | 合理但偏长期 | P3，当前解释器模式够用 |
| Dry Run / Breakpoint | 合理但偏长期 | P3，依赖前置架构 |
| Run History / HTML Report | 合理 | P2，和 manifest/hash 一起推进 |
| 自由连线节点图 | 不建议 | 会增加流程、循环、追溯复杂度 |

## 7. 推荐实施顺序

### 第一步：安全快照和追溯

1. 新增 `core/custom_test/snapshot.py`。
2. Run 前 clone 当前序列。
3. preflight 和 executor 都使用 snapshot。
4. 计算 `sequence_hash`。
5. 自动导出和 `ExportResult` 都写入 hash。
6. 运行期间冻结序列和属性编辑。

### 第二步：timeout/cancel 与 preflight 加固

1. 列出所有 instrument node 的 IO 调用点。
2. 标注每个调用是否有 timeout。
3. 对长等待改用 `context.sleep()` 或周期性检查 stop。
4. 对 adapter 增加可选 `timeout_s`。
5. 用 `PARAM_SCHEMA` 自动生成更多校验。
6. 对变量引用、分支作用域、RecordData 字段做更强 warning/error。

### 第三步：编辑效率

1. Palette 搜索。
2. 空状态引导。
3. Template Gallery。
4. Recent Sequences。
5. Copy/Paste/Duplicate。
6. Step 状态列。
7. Run Summary。

### 第四步：结果产品化

1. run folder。
2. manifest。
3. sequence snapshot。
4. events/logs。
5. chart 导出。
6. HTML report。

### 第五步：长期模型升级

1. 完整 `CustomTestDocument`。
2. v3 `view_state`。
3. Command Pattern。
4. Undo/Redo。
5. ExecutionEvent。
6. ExecutionPlan。
7. Dry Run/Breakpoint。
8. QAbstractItemModel。

## 8. 风险和注意事项

### 8.1 不要破坏模板兼容

模板目录约定为 `userdata/custom_test_templates/`。任何序列格式升级都必须通过 `load_sequence_file()` 兼容旧格式。

模板不应继续放在 `ui/pages/custom_test/` 内。UI 包只保留页面、控件和兼容 shim；模板属于项目/用户数据，应独立于 UI 实现目录。

### 8.2 不要删除 shim

`ui/pages/custom_test/executor.py`、`context.py`、`nodes/*` 对外部旧导入仍有价值。删除前必须全仓库 `rg` 确认引用，并提供迁移窗口。

### 8.3 不要让 core 依赖 Qt Widget

`core/custom_test/executor.py` 目前使用 `QObject/QThread/Signal`，这是历史折中。后续如要进一步纯化，可以拆成：

```text
core/custom_test/runner.py      # 纯 Python 执行逻辑
core/custom_test/executor.py    # Qt bridge / thread wrapper
```

这属于 P2/P3，不应阻塞 P0。

### 8.4 InstrumentManager 是主路径

后续仪器解析应继续围绕：

- `core/instruments/manager.py`
- `InstrumentResolver`
- `InstrumentLease`
- adapter 包装
- legacy fallback
- mock adapter

不建议为 Custom Test 另起一套独立仪器管理体系。

### 8.5 UI 优化要服务工程测试

Custom Test 是实验室工程工具，UI 应偏清晰、稳重、信息密度合理。优先优化真实工作流：

- 找节点。
- 看步骤。
- 改参数。
- 确认仪器。
- 运行中知道跑到哪一步。
- 数据能快速筛选、画图、导出。
- 出问题能定位到节点和参数。

## 9. 最终建议

这个 Optimize 方案经过适配后是合理的。推荐保留它的战略方向，但按当前项目状态调整为：

```text
当前 core/custom_test 基线
    -> P0 运行快照 + 只读态 + hash/manifest + timeout 审计
    -> P1 Palette/模板/复制粘贴/状态列/Run Summary
    -> P2 文档模型 v3 + Run History + HTML Report + Event
    -> P3 ExecutionPlan + Dry Run + Breakpoint + QAbstractItemModel
```

一句话结论：

> Custom Test 不需要重做；它需要沿着现有 `core/custom_test` 基线继续做安全、可追溯和可用性增强。原优化方案方向正确，但应降低大重构优先级，把近期工作集中在执行快照、运行态冻结、sequence hash、timeout/cancel、preflight/schema 和工程化 UI 体验上。
