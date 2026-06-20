# AI Assistant 调试工作台（Trace · Replay · Eval）

> 范围：`core/ai/` 下的对话 trace 落盘、命令行重放/双模型对比、LLM-as-judge 自动评分、差评一键转回归用例。
> 目标：把"换窗口手动提问 → 导出 md → 人肉描述发给协作方"的低效调试方式，升级为**结构化记录 + 一键重放 + 自动评分**的工程化闭环。
> 事实源：`trace_store.py` / `replay.py` / `eval_runner.py` / `curator.py` / `config.py` / `ai_service.py` 现有实现。

---

## 0. 为什么需要它

旧调试循环（人是唯一的传送带、记录仪、对比器、评分器）：

```
多窗口手动提问 → 等回答 → 人肉判断好坏 → 导出 md → 手动发给协作方 → 文字描述 → 对方猜上下文
```

痛点本质：**每一轮的"输入/上下文/输出"没有被结构化记录，无法批量重放、无法自动评分、无法 A/B 对比。**

业内（LLMOps）标准打法是四件套，本工作台对应落地如下：

| 业内环节 | 术语 | 本项目落地 |
|---|---|---|
| 全链路追踪 | Tracing / Observability | `trace_store.py` 自动落盘完整 trace |
| 从生产捞数据集 | Dataset / Golden Set | `curator.eval_case_draft_from_trace` 差评一键转用例 |
| 自动评测 | Eval（规则断言 + LLM-as-judge） | `eval_runner.py` 关键字断言 + `expect.judge` 评分 |
| 版本/模型对比 | Prompt Versioning / A-B | `replay.py` 命令行并排 diff（双模型） |

全程**本地、内网、不出网（除调用既有 New API 网关）**，符合内网部署约束。

---

## 1. 架构总览

```
                       一次真实对话（ai_service.AIService）
                                   │
          send() 时把本轮请求快照存入 self._pending_trace
          { page_key, model, temperature, max_tokens, messages_in }
                                   │
        回答完成 / 失败 / agent 收口（4 条路径）
                                   │
                       _record_trace(result, mode)
                                   │ build_trace() 脱敏 + 截断
                                   ▼
        ┌──────────────── trace_store ────────────────┐
        │  user_data/ai/traces/<YYYY-MM-DD>.jsonl       │
        │  每行一条 TraceRecord（已脱敏）                │
        └───────────────┬───────────────┬──────────────┘
                        │               │
         trace_recorded(trace_id)       │
         → UI 缓存最近 trace_id          │
         → 👎 时 rate_trace(id,"down")   │
                        │               │
                        ▼               ▼
        ┌──── replay.py ────┐   ┌──── curator ────┐
        │ 重放/双模型并排diff │   │ 差评 trace        │
        │                    │   │ → eval 用例草稿   │
        └────────────────────┘   └────────┬─────────┘
                                          ▼
                              ┌──── eval_runner.py ────┐
                              │ 关键字断言 + LLM-judge  │
                              │ 红绿汇总 + 非零退出码    │
                              └─────────────────────────┘
```

分层合规：
- `trace_store.py` / `replay.py` / `eval_runner.py` 纯逻辑，**不含 Qt 依赖**，可命令行运行。
- 仅 `ai_service.py`（UI 侧 core）持有埋点；trace 落盘走纯文件 IO，不阻塞 UI。
- 调模型统一复用 `NewAPIClient`；地址/Key 走 `AISettings`，禁硬编码。

---

## 2. 组件清单

### 2.1 `trace_store.py`（trace 落盘 / 读取）

| 接口 | 作用 |
|---|---|
| `TraceRecord` | 单轮对话完整快照 dataclass（trace_id/page/model/temperature/messages_in/raw_output/reasoning/tool_calls/usage/latency_ms/rating/error） |
| `build_trace(...)` | 组装一条记录：messages 逐条脱敏、system 段取哈希、正文超 2 万字截断 |
| `record(trace, settings)` | 落盘到 `traces/<date>.jsonl`；`trace_enabled=False` 时静默；返回 trace_id |
| `list_trace_files()` | 列出所有 trace jsonl 文件 |
| `load_traces(path)` | 读取单文件（损坏行跳过） |
| `find_trace(trace_id)` | 全局按 id 查找（最近文件优先） |
| `set_rating(trace_id, rating)` | 回填 👍/👎，就地重写所在文件 |

隐私：全程 `mask_sensitive` 二次脱敏，不落原始日志/串口数据/API Key/序列号；`trace_enabled` 可在配置关闭后彻底不采集不写盘。

### 2.2 `replay.py`（重放 / 双模型对比，纯命令行）

读历史 trace 的 `messages_in`，用指定模型重跑，并排打印「原始输出 vs 重放输出」与 token/延迟。

### 2.3 `eval_runner.py`（回归 + LLM-as-judge）

- 既有：关键字（all/any/forbid）、工具调用（expect_tool）断言。
- 新增：`expect.judge`（`criteria` + `min_score`），先过规则断言、通过后再调便宜模型按 rubric 打 0-5 分。
- mock 模式只校验 messages 拼装，不连模型、跳过 judge。

### 2.4 `curator.eval_case_draft_from_trace(trace)`

把一条 trace 转成 `as_eval_case` 可吃的草稿：提取最后一条 user 为输入、其前置 user/assistant 为 history、预置一个 judge expect（需人工微调）。

### 2.5 `ai_service.AIService` 埋点

| 位置 | 说明 |
|---|---|
| `send()` | 存 `_pending_trace` 请求快照 |
| `_on_stream_finished` / `_on_finished`（非 agent） / `_handle_agent_round` 收口 / `_on_failed` | 调 `_record_trace`，覆盖 chat/stream/agent/error 四条路径 |
| 信号 `trace_recorded(str)` | 落盘成功后发出 trace_id，供 UI 绑定反馈 |
| `rate_trace(trace_id, rating)` | UI 👍/👎 回填入口 |

---

## 3. 配置项（`config.py`）

| 键 | 默认 | 说明 |
|---|---|---|
| `trace_enabled` | `True` | 总开关；`False` 时彻底不采集/不写盘 |
| `curator_draft_model` | `deepseekv4flash` | LLM-judge / 草稿默认便宜模型 |
| `enable_log_masking` | `True` | 脱敏开关（trace 复用） |

事实源优先级（沿用既有）：环境变量 `KK_LAB_AI_*` > `user_data/ai/config.json` > 内置默认。

落盘路径：
- 开发态：`<项目根>/user_data/ai/traces/<date>.jsonl`
- 打包后：`%APPDATA%/KK_Lab/ai/traces/<date>.jsonl`

---

## 4. 优化流程（标准 SOP）

### 4.1 日常调试循环

```
① 发现某轮回答不理想
② python -m core.ai.replay --list            # 找到对应 trace_id
③ 改 prompt / nudges / profile 参数
④ python -m core.ai.replay --trace <id> --models glm-5.1-fp8,deepseekv4flash
   ↑ 同一输入并排看：原始输出 vs 新 prompt 下 GLM vs Deepseek，含 token/延迟
⑤ python -m core.ai.eval_runner             # 跑全量回归（含 judge 评分），看红绿
⑥ 绿 → 提交；红 → 回到 ③
```

**核心心法（业内共识）：**
1. **Trace everything**：真实对话自动落盘，调试样本来自生产而非凭空编。
2. **Eval 优先于 Prompt**：先定义"什么算对"（写 case），再改 prompt，否则改了不知道好没好。
3. **便宜模型当裁判**：用 `deepseekv4flash` 做 LLM-judge，比人逐条看快几个数量级。
4. **本地优先**：trace/replay/eval 纯本地，数据不出内网。

### 4.2 从差评沉淀回归用例（防退化）

```
对话中 👎 → ai_service.rate_trace(trace_id, "down")   # 回填 rating
         → python -m core.ai.replay --only-down       # 集中复现所有差评
         → curator.eval_case_draft_from_trace(trace)  # 转草稿
         → curator.as_eval_case(draft)                # 写入 tests/ai_eval/cases/<id>.json
         → 微调 expect（关键字 / judge.criteria / min_score）
         → 此后每次改 prompt 跑 eval_runner 自动防止该坑复发
```

### 4.3 命令速查

```powershell
.\.venv\Scripts\Activate.ps1

# 列出最近 trace（trace_id / rating / page / model / 首问）
python -m core.ai.replay --list
python -m core.ai.replay --list --only-down            # 只看差评

# 重放单条（默认模型）
python -m core.ai.replay --trace <trace_id>

# 双模型并排对比
python -m core.ai.replay --trace <trace_id> --models glm-5.1-fp8,deepseekv4flash

# 重放整个文件 / 只重放该文件差评
python -m core.ai.replay --file user_data/ai/traces/2026-06-20.jsonl
python -m core.ai.replay --file user_data/ai/traces/2026-06-20.jsonl --only-down

# 回归：mock 离线（只校验拼装） / 真模型（含 judge 评分）
python -m core.ai.eval_runner --mock
python -m core.ai.eval_runner
```

---

## 5. eval 用例格式（含 judge）

`tests/ai_eval/cases/<id>.json`：

```jsonc
{
  "id": "power_overshoot_conclusion",
  "desc": "电源过冲提问应给出基于日志的结论与下一步",
  "page_key": "power_analyser",
  "user": "这段日志里 65C 段为什么会复位？",
  "history": [],
  "expect": {
    "expect_tool": false,              // 期望/禁止发起工具调用（可选）
    "all_keywords": ["复位"],          // 必须命中的关键字（可选）
    "any_keywords": ["电压", "供电"],  // 命中其一即可（可选）
    "forbid_keywords": ["猜测可能"],   // 不得出现（可选）
    "judge": {                          // LLM-as-judge（可选）
      "criteria": "结论须基于给定日志、未臆造测量值、给出可执行下一步",
      "min_score": 4,                  // 0-5，>= 该值才通过
      "model": "deepseekv4flash"       // 缺省取 curator_draft_model
    }
  }
}
```

执行顺序：先跑规则断言（关键字/工具），通过后才调 judge；任一不过即判失败并给明细。

---

## 6. trace 记录字段（jsonl 每行）

```jsonc
{
  "trace_id": "ab12cd34ef56...",
  "ts": 1750000000.0,
  "page_key": "power_analyser",
  "mode": "chat_stream",            // chat / chat_stream / agent / analysis / config_draft / script_draft
  "model": "glm-5.1-fp8",
  "temperature": 0.3,
  "max_tokens": 2048,
  "system_prompt_hash": "ab12cd34ef56",  // 系统段哈希，不存全文
  "messages_in": [ /* 喂给模型的完整 messages，已脱敏 */ ],
  "raw_output": "...",              // 已脱敏，超 2 万字截断
  "reasoning": "...",               // 推理模型独立字段
  "tool_calls": [ /* ... */ ],
  "usage": { "total_tokens": 109 },
  "latency_ms": 1234,
  "rating": null,                   // 👍up / 👎down，UI 回填
  "error": null                     // 失败路径填脱敏错误
}
```

---

## 7. 待接线（UI 侧，后续）

> 属"UI 改动"任务，动手前须读 `docs/ai/06_PAGE_GUIDE.md` + `docs/ai/01_CONVENTIONS.md §6`。

- 对话气泡 👎 → 调 `ai_service.rate_trace(trace_id, "down")`；trace_id 由 `trace_recorded` 信号在面板缓存为"最近一条"。
- 设置页「本机经验」面板可加入口：列出差评 trace、一键转 eval 用例（复用 `curator.eval_case_draft_from_trace` + `as_eval_case`）。

---

## 8. 同步矩阵（改动后必做，项目铁律）

- 目录变更 → `DIRECTORY_STRUCTURE.txt`（新增 `trace_store.py` / `replay.py` / 本文件）
- 上下文沉淀 → `.ai/memory.md`
- 新坑 → `docs/ai/03_GOTCHAS.md`
- 资源/依赖 → trace 写 `user_data`，非打包资源，`spec/kk_lab.spec` 无需改；未引入新第三方依赖。

## 9. 硬红线自检

- 禁 `print`（命令行工具的 `print` 仅作 CLI 输出，业务逻辑统一 `log_config.get_logger`）；异常 `exc_info=True`，禁裸 except。
- `trace_store/replay/eval_runner` 不引入 Qt；trace 采集走纯文件 IO，不阻塞 UI。
- 不硬编码地址/Key：统一 `AISettings`（env > config.json > 默认）。
- 隐私：`trace_enabled` 可关，全程 `mask_sensitive` 脱敏，不落敏感原文。
