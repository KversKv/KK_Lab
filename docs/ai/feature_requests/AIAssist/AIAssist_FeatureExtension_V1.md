# AI Assist 功能增补 V1：波形分析 / 受控控制 / 用量统计 / 序列优化 / Markdown

> 📚 **AI Assist 文档索引**
> | 文档 | 角色 |
> |---|---|
> | [AIAssist_Architecture.md](./AIAssist_Architecture.md) | 架构设计与规范（事实源） |
> | [AIAssist_ImplementationPlan.md](./AIAssist_ImplementationPlan.md) | 主实现计划与进度表（阶段 0~5） |
> | **[AIAssist_FeatureExtension_V1.md](./AIAssist_FeatureExtension_V1.md)**（本文） | 功能增补 V1（波形/控制/用量/序列/Markdown，Phase A~C） |

> 配套主文档：[AIAssist_Architecture.md](./AIAssist_Architecture.md)（架构事实源）、[AIAssist_ImplementationPlan.md](./AIAssist_ImplementationPlan.md)（主进度表）。
> 本文定位：在主架构之上，落地 6 个真实工程难题的解决方案与实现步骤。属**补充任务**，规划为 Phase A / B / C（预计 2~3 次会话完成）。
> 分层铁律：`main.py → ui/ ←→ core/ → instruments/ → lib/`；`instruments/` 禁 Qt；`ui/` 禁阻塞 IO（QThread + Signal/Slot）；禁 `print`、异常 `exc_info=True`、禁裸 `except`。
> 状态：`☐ 待办` / `◐ 进行中` / `☑ 完成` / `⊘ 阻塞` / `— 不适用`。

---

## 0. 增补特性总览

| # | 特性 | 核心策略 | 复用现状 | 归属 Phase |
|---|---|---|---|---|
| F1 | 波形喂 AI | 统计摘要 + LTTB 降采样 + 按需放大三层，**不传原始点** | Datalog `{time,values}` + 已有 Min/Avg/Max | A |
| F2 | 受控仪器/UI 控制 | 风险分级 + IDE 式确认 + 带护栏白名单 + 硬熔断 | AI_Assist §8/§10 Action 框架 | B |
| F3 | Token / 速度统计 | 读响应 `usage` 真值 + 客户端计时 | NewAPIClient / AIService | A |
| F4 | UI 操作覆盖 | 语义 Action 注册表（非全像素），分批登记 | AI_Assist §8 | B |
| F5 | 内存序列优化 | in-memory dict 往返 + preflight + diff 预览，**免文件** | `core/custom_test/serialization` data 级入口 | C |
| F6 | Markdown 渲染 | `QTextBrowser.setMarkdown()` 起步，代码块可复制 | ChatView | A |

> Phase 划分原则：A=面板内即可见的体验底座（Markdown/用量/波形摘要）；B=受控控制闭环（折衷安全）；C=序列智能优化（最依赖 custom_test）。

---

## 1. F1 波形数据喂给 AI（三层结构）

### 1.1 问题
20μs × 30s = **150 万点/通道**。原始点直接传 → 撑爆上下文且 LLM 读不懂；截图 → 丢数值精度。

### 1.2 方案：摘要 / 降采样 / 按需放大三层
**第 1 层 统计摘要（永远先传）**：均值/最大/最小/峰峰/标准差 + 采样率/点数 + 异常点（阈值穿越）列表 + 稳态段识别。几百字即可让 AI 有效分析。
**第 2 层 LTTB 降采样（要看形状时）**：Largest-Triangle-Three-Buckets 把 150 万点降到 500~2000 点，保留视觉峰谷。业内画图降采样事实标准。
**第 3 层 按需放大（drill-down）**：AI 指定时间窗 → 从原始数据切片高分辨率片段（如 ±50ms / 2500 点）再传。等于给 AI 一个 zoom 工具。

> 原始 150 万点**永远留在本地**，AI 只见摘要/降采样/切片。
> 可选多模态：若内网模型支持视觉，可截图 + 摘要双发（图看形态、文字给数值）；非必须，第 1 层覆盖 ~80% 场景。

### 1.3 数据结构（草案）
```python
@dataclass
class WaveformStat:
    label: str            # "VBUS CH1 I"
    unit: str             # "mA"
    sample_period_s: float
    point_count: int
    minimum: float; maximum: float; average: float
    peak_to_peak: float; std: float
    anomalies: list[dict] # [{"t":2.1,"value":480,"type":"spike"}]
    steady_segments: list[dict]  # [{"start":10,"end":25,"avg":11.8,"std":0.3}]

@dataclass
class WaveformDigest:
    stats: list[WaveformStat]
    downsampled: dict[str, dict]  # {label:{"time":[...],"values":[...]}} LTTB 后
    note: str                      # "原始 150 万点已降采样至 1500 点"
```

### 1.4 实现位置
- `core/ai/providers/waveform_provider.py`：`build_digest(all_data, max_points=1500, anomaly_sigma=3)` + `slice_window(all_data, label, t0, t1)`。
- LTTB：先查 `pyqtgraph` 是否已内置可复用；否则在 provider 内实现纯算法（不依赖 Qt）。
- Datalog 页面提供"发送当前波形给 AI"入口（读其内存 `all_data`）。

### 1.5 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F1.1 | `WaveformStat`/`WaveformDigest` dataclass | `core/ai/schemas.py` | ☐ |
| F1.2 | LTTB 降采样（纯算法 / 复用 pyqtgraph） | `core/ai/providers/waveform_provider.py` | ☐ |
| F1.3 | 统计摘要 + 异常点 + 稳态段识别 | 同上 | ☐ |
| F1.4 | 按需放大 `slice_window()` + AI drill-down action | 同上 + actions | ☑ |
| F1.5 | Datalog 页面"发送波形给 AI"入口（读内存 all_data） | Datalog UI 接线 | ☐ |
| F1.6 | digest → prompt 文本化模板 | `core/ai/prompt_manager.py` | ☐ |

---

## 2. F2 受控仪器/UI 控制（安全折衷：4 层防线）

### 2.1 方案：分级 + 确认 + 白名单(带护栏) + 熔断
**① 风险分级**（落实 AI_Assist §10）

| 等级 | 示例 | 默认策略 |
|---|---|---|
| low 只读 | 查仪器状态/读会话/读日志 | AI 直接执行，不打扰 |
| medium 软操作 | 切页面/改 UI 配置（不下发硬件） | 直接执行 + 审计 |
| high 硬件输出 | 设电压/电流、串口发送、启动测试 | 逐次弹窗确认（IDE 式） |
| critical 危险 | 超量程、删文件、批量下发 | 默认禁 AI 执行，仅生成草案给人 |

**② IDE 式确认**：`high` 动作弹 `ActionConfirmDialog`，展示"做什么 + 参数 + 影响范围"。
**③ 白名单（带护栏，解决自动测试被打断）**：
- 会话级白名单（本次会话自动批准 X 动作）；
- 常驻白名单 `user_data/ai/policy.json`；
- **护栏 = 白名单必带边界条件**（如 `set_voltage` 仅 ≤5V 且 ≤1A 自动批准），非无脑放行。这是硬件控制与普通 IDE Agent 的本质区别。
- 序列运行中（已过 preflight + 用户点 Run）= 隐式白名单窗口，AI 监测/执行不再逐步打扰。

**④ 硬熔断（不可绕过）**：超物理量程/SCPI 安全范围的指令在 `instruments/` 层拒绝，AI 与白名单都无法突破。

### 2.2 policy.json 草案
```json
{
  "version": 1,
  "auto_approve": [
    {"action": "set_voltage", "when": {"voltage_max": 5.0, "current_max": 1.0}},
    {"action": "open_page"}
  ],
  "session_grants": [],
  "blocked": ["delete_file", "factory_reset"]
}
```

### 2.3 决策链（dispatcher 内）
```
AI 请求动作
  → 风险分级 RiskPolicy
  → blocked? → 拒绝 + 审计
  → low/medium? → 执行
  → high? → 命中白名单(护栏校验通过)? → 执行 ; 否则弹确认
  → critical? → 不执行，转"生成草案给人手动"
  → 执行前再过 instruments 层硬熔断
  → 全程审计（含拒绝/取消）
```

### 2.4 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F2.1 | `RiskPolicy` + 动作风险等级表 | `core/ai/actions/permission.py` | ☑ |
| F2.2 | `policy.json` 读写 + 护栏条件求值 | `core/ai/actions/policy.py` | ☑ |
| F2.3 | `ActionConfirmDialog`（parent=面板，OK/Cancel 二元化） | `ui/ai/action_confirm_dialog.py` | ☑ |
| F2.4 | 会话级"自动批准本动作"勾选 + 常驻白名单写入 | dialog + policy | ☑ |
| F2.5 | dispatcher 决策链接入 + 序列运行隐式白名单 | `core/ai/actions/dispatcher.py` | ☑ |
| F2.6 | instruments 层硬熔断校验点核查（量程/安全） | 复用现有驱动校验 | ☑ |
| F2.7 | 审计日志 `user_data/ai/audit.log`（含拒绝/取消） | `core/ai/actions/audit.py` | ☑ |

---

## 3. F3 Token 与速度统计

### 3.1 方案：响应 usage 真值 + 客户端计时
OpenAI 兼容响应含 `usage{prompt_tokens, completion_tokens, total_tokens}`。

| 指标 | 来源 | 算法 |
|---|---|---|
| 最近 输入/输出 tokens | `usage.*` | 直接读 |
| 会话累计 输入/输出 | 累加 usage | 客户端累加 |
| 输出速度 tok/s | `completion_tokens ÷ 响应耗时` | 客户端计时 |
| 首字延迟 TTFT | 第一个 chunk 时刻 - 发送时刻 | **仅流式** |

**坑**：非流式只能算整体平均速度，**测不了 TTFT**（TTFT/实时 TPS 留待流式 Phase 5）；**禁用 tiktoken 当真值**（内网模型分词器可能不同，仅可用于发送前预估裁剪）。

### 3.2 数据结构
```python
@dataclass
class TurnUsage:
    prompt_tokens: int; completion_tokens: int; total_tokens: int
    elapsed_ms: int
    output_tps: float   # completion_tokens / (elapsed_ms/1000)

@dataclass
class SessionStats:
    requests: int = 0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    def add(self, t: TurnUsage): ...
```

### 3.3 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F3.1 | `NewAPIClient` 返回带 `usage` + `elapsed_ms` | `core/ai/newapi_client.py` | ☐ |
| F3.2 | `TurnUsage` / `SessionStats` | `core/ai/schemas.py` | ☐ |
| F3.3 | `AIService` 维护 SessionStats + 信号 `usage_updated` | `core/ai/ai_service.py` | ☐ |
| F3.4 | 面板底部状态栏：本次 ↑/↓ @ tok/s ｜ 会话累计 | `ui/ai/ai_assist_panel.py` | ☐ |
| F3.5 | 数值 QLabel 带单位（tokens / tok·s⁻¹），符合铁律 | 同上 | ☐ |

---

## 4. F4 UI 操作覆盖（语义 Action 注册表）

### 4.1 方案
**目标不是覆盖全部像素操作，而是覆盖所有有业务意义的语义动作。** 选路线 A（语义 Action 注册表，AI_Assist §8 已定），**拒绝**路线 B（反射点任意按钮，对硬件软件是灾难）。

分批登记，按价值优先级：
1. 导航 + 查询（low，量大价值高）；
2. 核心测试流程（run/stop sequence、set voltage）；
3. 边角操作。

**覆盖率指标**：不是"能点多少按钮"，而是"用户常说的指令能做到几成"。维护一张 Action 清单表对照页面逐条登记。

### 4.2 Action 清单（按页面登记，节选模板）
| 页面 | 动作 | 风险 | 落点 |
|---|---|---|---|
| 全局 | open_page / toggle_ai_panel | low/medium | nav / main_window |
| Datalog | query_datalog_state / send_waveform_to_ai / export_datalog | low/high | Datalog UI |
| Power Analyser | query_channel / set_voltage / channel_on_off | low/high | InstrumentManager |
| Serial | query_serial_state / send_serial / clear_rx | low/high | SerialSessionManager |
| Custom Test | get_sequence / run / stop / apply_optimized_sequence | low/high | custom_test runner |

### 4.3 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F4.1 | `ActionSpec` + `ActionRegistry`（注册/查找/渲染 tools） | `core/ai/actions/registry.py` | ☐ |
| F4.2 | Action 清单表落档（对照各页面逐条登记） | 本文 §4.2 维护 | ☐ |
| F4.3 | handlers 分批实现（导航查询→核心流程→边角） | `core/ai/actions/handlers/` | ☐ |
| F4.4 | 多轮 tool-calling：执行结果回灌 AIService | `core/ai/ai_service.py` | ☐ |

---

## 5. F5 内存序列优化（免文件往返）

### 5.1 方案：in-memory dict 往返 + preflight + diff
你的代码已具备全部基础设施，无需"存文件→导入"：
- `SequenceCanvas` 内存持有 `CustomTestSequence`；
- `core/custom_test/serialization.py` 已能 **dict ↔ 节点树** 互转（文件仅是 `json.dump` 薄壳，用 data 级入口而非 file 级）；
- `validation.preflight()` 校验内存序列。

**工作流**：
```
1 读：serialization 导出当前画布为 v2 dict（内存）+ 用户提示词 → AI
2 改：AI 返回 优化后 dict 或 patch
3 校：反序列化 + preflight（拦非法节点/变量/仪器）
4 看：ConfigPreview 展示 before/after diff
5 应用：load 回 SequenceCanvas（应用前快照，可撤销）
```

**关键设计**：
- 完整 vs patch：默认返回完整 dict（短序列最稳）；长序列让 AI 返回结构化 patch（省 token、diff 清晰）。两者都支持。
- **必经 preflight 再落画布**：error 阻止应用，warning 提示可继续。
- **可撤销**：应用前快照当前序列，支持"撤销 AI 修改"。

### 5.2 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F5.1 | `SequenceContextProvider`：读画布 → v2 dict（data 级） | `core/ai/providers/sequence_provider.py` | ☑ |
| F5.2 | patch 模型 + 应用器（插入/删除/改参，作用于 dict） | `core/ai/sequence_patch.py` | ☑ |
| F5.3 | AI 输出（完整/patch）→ 反序列化 + preflight 校验 | 接 `core/custom_test` | ☑ |
| F5.4 | 序列 before/after diff 视图（增强 ScriptPreview） | `ui/ai/script_preview.py` | ☑ |
| F5.5 | 应用回画布 + 应用前快照 + 撤销 | Custom Test UI 接线 | ☑ |

---

## 6. F6 Markdown 渲染

### 6.1 方案
AI 默认输出 Markdown，对话 UI 必须渲染，否则代码/表格挤成一团。按成本：

| 方案 | 能力 | 成本 | 采用 |
|---|---|---|---|
| `QTextBrowser.setMarkdown()` | 标题/列表/粗体/表格/链接 | 零依赖 | **Phase A 起步** |
| `markdown` + Pygments → HTML | + 代码语法高亮 | +2 依赖 | Phase 5 体验升级 |
| QWebEngine | 完整(mermaid/数学) | 重，增打包 | 不采用（违反不增包原则） |

**要点**：
- 代码块**一键复制**（SCPI/脚本/JSON 刚需）；
- `setMarkdown()` 不做代码高亮，需高亮再上 markdown+Pygments；
- 流式时增量重渲染（短消息整段重 `setMarkdown` 即可）；
- **结构化结果**（日志分析 Schema、序列 diff）**不走自由 Markdown**，返回 JSON 由固定 UI 组件渲染，更可控。Markdown 仅用于自由对话。

### 6.2 任务
| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F6.1 | ChatView 用 `QTextBrowser.setMarkdown()` 渲染助手消息 | `ui/ai/chat_view.py` | ☐ |
| F6.2 | 代码块识别 + 一键复制按钮 | 同上 | ☐ |
| F6.3 | 链接点击策略（外链/内部跳转）+ 安全过滤 | 同上 | ☐ |
| F6.4 | 结构化结果走固定组件（不混入 Markdown） | chat_view + schemas | ☐ |

---

## 7. 实现 Phase 规划（补充任务，预计 2~3 次会话）

### 7.0 Phase 总览看板

| Phase | 主题 | 状态 | 含特性任务 | 依赖 | 关键交付 |
|---|---|---|---|---|---|
| A | 体验底座（Markdown + 用量 + 波形摘要） | ☐ | F6.1~F6.4 / F3.1~F3.5 / F1.1~F1.3、F1.5~F1.6 | 主计划阶段 1 面板骨架 | 对话 Markdown + 用量条 + 波形摘要分析 |
| B | 受控控制闭环（安全折衷 + Action 覆盖） | ☑ | F2.1~F2.7 / F4.1~F4.4 / F1.4 | Phase A + 主计划阶段 1 | 4 层防线 + 语义 Action + drill-down |
| C | 序列智能优化（免文件往返） | ☑ | F5.1~F5.5 | Phase A、B + custom_test | 读画布→优化→校验→diff→应用→可撤销 |

> 状态：`☐ 待办` / `◐ 进行中` / `☑ 完成` / `⊘ 阻塞` / `— 不适用`。
> 若进度紧张，Phase A 可独立交付（已显著提升体验）；B、C 可顺延但不拆散（安全/序列各自需完整闭环）。

---

### 7.A Phase A：体验底座（Markdown + 用量 + 波形摘要）
> 面板内立即可见的价值，零/低依赖，风险最低，先做。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F6.1 | ChatView 用 `QTextBrowser.setMarkdown()` 渲染助手消息 | `ui/ai/chat_view.py` | ☐ |
| F6.2 | 代码块识别 + 一键复制按钮 | `ui/ai/chat_view.py` | ☐ |
| F6.3 | 链接点击策略（外链/内部跳转）+ 安全过滤 | `ui/ai/chat_view.py` | ☐ |
| F6.4 | 结构化结果走固定组件（不混入 Markdown） | `ui/ai/chat_view.py` + `core/ai/schemas.py` | ☐ |
| F3.1 | `NewAPIClient` 返回带 `usage` + `elapsed_ms` | `core/ai/newapi_client.py` | ☐ |
| F3.2 | `TurnUsage` / `SessionStats` | `core/ai/schemas.py` | ☐ |
| F3.3 | `AIService` 维护 SessionStats + 信号 `usage_updated` | `core/ai/ai_service.py` | ☐ |
| F3.4 | 面板底部状态栏：本次 ↑/↓ @ tok/s ｜ 会话累计 | `ui/ai/ai_assist_panel.py` | ☐ |
| F3.5 | 数值 QLabel 带单位（tokens / tok·s⁻¹） | `ui/ai/ai_assist_panel.py` | ☐ |
| F1.1 | `WaveformStat`/`WaveformDigest` dataclass | `core/ai/schemas.py` | ☐ |
| F1.2 | LTTB 降采样（纯算法 / 复用 pyqtgraph） | `core/ai/providers/waveform_provider.py` | ☐ |
| F1.3 | 统计摘要 + 异常点 + 稳态段识别 | `core/ai/providers/waveform_provider.py` | ☐ |
| F1.5 | Datalog 页面"发送波形给 AI"入口（读内存 all_data） | Datalog UI 接线 | ☐ |
| F1.6 | digest → prompt 文本化模板 | `core/ai/prompt_manager.py` | ☐ |

**Phase A 验收**：
- ☐ 助手消息 Markdown 正常渲染 + 代码块一键复制；
- ☐ 面板显示本次/会话 输入·输出 token 与输出 tok/s；
- ☐ Datalog 波形能以"摘要+降采样"发给 AI 并得到分析；
- ☐ 不引入大型 AI 框架/向量库；QThread 不阻塞；无 print / exc_info / 无裸 except。

---

### 7.B Phase B：受控控制闭环（安全折衷 + Action 覆盖）
> 安全是硬件软件生命线，单独成阶段。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F2.1 | `RiskPolicy` + 动作风险等级表 | `core/ai/actions/permission.py` | ☑ |
| F2.2 | `policy.json` 读写 + 护栏条件求值 | `core/ai/actions/policy.py` | ☑ |
| F2.3 | `ActionConfirmDialog`（parent=面板，OK/Cancel 二元化） | `ui/ai/action_confirm_dialog.py` | ☑ |
| F2.4 | 会话级"自动批准本动作"勾选 + 常驻白名单写入 | dialog + policy | ☑ |
| F2.5 | dispatcher 决策链接入 + 序列运行隐式白名单 | `core/ai/actions/dispatcher.py` | ☑ |
| F2.6 | instruments 层硬熔断校验点核查（量程/安全） | 复用现有驱动校验 | ☑ |
| F2.7 | 审计日志 `user_data/ai/audit.log`（含拒绝/取消） | `core/ai/actions/audit.py` | ☑ |
| F4.1 | `ActionSpec` + `ActionRegistry`（注册/查找/渲染 tools） | `core/ai/actions/registry.py` | ☑ |
| F4.2 | Action 清单表落档（对照各页面逐条登记） | 本文 §4.2 维护 | ☑ |
| F4.3 | handlers 分批实现（导航查询→核心流程→边角） | `core/ai/actions/handlers/` | ☑ |
| F4.4 | 多轮 tool-calling：执行结果回灌 AIService | `core/ai/ai_service.py` | ☑ |
| F1.4 | 按需放大 `slice_window()` + AI drill-down action | `core/ai/providers/waveform_provider.py` + actions | ☑ |

**Phase B 验收**：
- ☑ low 直执行、high 弹确认、白名单带护栏自动批准、critical 禁执行；
- ☑ instruments 层硬熔断生效（AI/白名单均不可绕过）；全程审计含拒绝/取消；
- ☑ AI 可经语义 Action 跳页/查状态/控仪器（高风险确认）；
- ☑ 仪器一律经 InstrumentManager，AI 无法绕过 `instruments/`。

---

### 7.C Phase C：序列智能优化（免文件往返）
> 最依赖 custom_test，放最后。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| F5.1 | `SequenceContextProvider`：读画布 → v2 dict（data 级） | `core/ai/providers/sequence_provider.py` | ☑ |
| F5.2 | patch 模型 + 应用器（插入/删除/改参，作用于 dict） | `core/ai/sequence_patch.py` | ☑ |
| F5.3 | AI 输出（完整/patch）→ 反序列化 + preflight 校验 | 接 `core/custom_test` | ☑ |
| F5.4 | 序列 before/after diff 视图（增强 ScriptPreview） | `ui/ai/script_preview.py` | ☑ |
| F5.5 | 应用回画布 + 应用前快照 + 撤销 | Custom Test UI 接线 | ☑ |

**Phase C 验收**：
- ☑ AI 读当前画布序列 → 按提示词优化 → preflight 校验 → diff 预览 → 应用回画布（可撤销）；
- ☑ 全程不落盘、无需手动导入；error 阻止应用、warning 提示可继续。

---

## 8. 验收总表

| # | 验收点 | Phase |
|---|---|---|
| 1 | 波形以摘要+降采样发 AI，不传原始点，可 drill-down 放大 | A/B |
| 2 | low 直执行 / high 确认 / 白名单带护栏 / critical 禁 / 硬熔断 / 全审计 | B |
| 3 | 显示本次与会话累计 输入/输出 token 及输出 tok/s | A |
| 4 | AI 经语义 Action 覆盖导航/查询/核心测试流程（分批可扩） | B |
| 5 | AI 读内存序列→优化→校验→diff→应用→可撤销，免文件 | C |
| 6 | 助手消息 Markdown 渲染，代码块一键复制 | A |
| 7 | 全程符合分层铁律 / QThread 不阻塞 / 无 print / exc_info / 无裸 except | A/B/C |
| 8 | 不引入大型 AI 框架/向量库，打包体积不显著增长 | A/B/C |

---

## 9. 同步矩阵（每 Phase 完成必做）

| 改动 | 需同步 |
|---|---|
| 新增 `core/ai/providers/*`、`core/ai/actions/*`、`core/ai/sequence_patch.py` | `DIRECTORY_STRUCTURE.txt` |
| 新增 SVG 图标（复制/发送/放大等） | `resources/` + `spec/kk_lab.spec` |
| 新增依赖（如 Phase5 markdown/Pygments） | `requirements.txt` |
| 白名单/护栏/critical 边界等安全决策 | `docs/ai/decisions/` |
| 关键上下文沉淀 | `.ai/memory.md` |
| 模块单独迭代 | 对应 `__init__.py` 的 `MODULE_VERSION` +1 |
| 改完 | 跑 lint |

---

## 10. 风险登记

| 风险 | 影响 | 缓解 |
|---|---|---|
| 内网模型上下文窗口小 | 波形/日志摘要质量 | LTTB 降采样 + 摘要 + drill-down 分次 |
| 模型不支持原生 tools | F4 动作能力 | response_parser 降级 JSON（AI_Assist §9） |
| 白名单被滥用绕过安全 | 硬件损坏 | 护栏边界 + instruments 层硬熔断不可绕过 |
| AI 生成非法序列 | 画布损坏 | 必经 preflight + 应用前快照可撤销 |
| Markdown 高亮需新依赖 | 打包体积 | Phase A 用零依赖 setMarkdown，高亮留 Phase 5 |
| 非流式测不了 TTFT | 速度指标不全 | 先给整体平均 tok/s，TTFT 待流式 Phase 5 |
