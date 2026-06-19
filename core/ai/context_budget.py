"""上下文预算与裁剪（AI_Assistant_MD §2.3 / Phase 1）。

按「当前实际模型」的上下文窗口控制 messages 总量：
  预算 = window - reserve_output；
  固定保留 system 段 + 本轮 user；
  动态上下文块（日志/波形）单独限额，超额先裁它们（保头尾、中段省略）；
  历史从最旧往前裁，直到落入预算。

token 估算优先用 tiktoken，缺失则启发式：中文≈1.5 token/字，英文≈1 token/4 字。
窗口必须「按模型」取，不写死全局值；未知模型回退到最小已知窗口（保守不溢出）。
"""
from __future__ import annotations

from log_config import get_logger

logger = get_logger(__name__)

try:
    import tiktoken as _tiktoken
except ImportError:
    _tiktoken = None

_ENCODING = None


def _get_encoding():
    global _ENCODING
    if _tiktoken is None:
        return None
    if _ENCODING is None:
        try:
            _ENCODING = _tiktoken.get_encoding("cl100k_base")
        except Exception:
            logger.info("tiktoken 编码加载失败，回退启发式 token 估算", exc_info=True)
            _ENCODING = None
    return _ENCODING


def estimate_tokens(text: str) -> int:
    """估算文本 token 数：优先 tiktoken，缺失则按中英文启发式。"""
    if not text:
        return 0
    enc = _get_encoding()
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            logger.info("tiktoken 编码失败，回退启发式", exc_info=True)
    cjk = 0
    other = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u30ff":
            cjk += 1
        else:
            other += 1
    return int(cjk * 1.5 + other / 4 + 0.5)


def _message_tokens(message: dict) -> int:
    content = message.get("content") or ""
    total = estimate_tokens(content) + 4
    tool_calls = message.get("tool_calls")
    if tool_calls:
        try:
            import json

            total += estimate_tokens(json.dumps(tool_calls, ensure_ascii=False))
        except Exception:
            pass
    return total


def resolve_window(model: str, windows: dict[str, int], default_window: int) -> int:
    """按当前模型取上下文窗口；未知模型回退到最小已知窗口（保守）。"""
    if model and model in windows:
        try:
            return int(windows[model])
        except (TypeError, ValueError):
            pass
    if windows:
        try:
            return min(int(v) for v in windows.values())
        except (TypeError, ValueError):
            pass
    return int(default_window)


def clip_context_block(text: str, max_tokens: int) -> str:
    """把单个上下文块裁到 max_tokens 以内：保头尾、中段以省略标记替换。"""
    if max_tokens <= 0 or estimate_tokens(text) <= max_tokens:
        return text
    lines = text.splitlines()
    if len(lines) <= 4:
        approx_chars = max(1, max_tokens * 2)
        if len(text) <= approx_chars:
            return text
        head = text[: approx_chars // 2]
        tail = text[-approx_chars // 2:]
        return f"{head}\n…[上下文过长，已省略中段]…\n{tail}"

    head_lines: list[str] = []
    tail_lines: list[str] = []
    budget = max_tokens
    i, j = 0, len(lines) - 1
    take_head = True
    while i <= j and budget > 0:
        if take_head:
            cost = estimate_tokens(lines[i]) + 1
            if cost > budget:
                break
            head_lines.append(lines[i])
            budget -= cost
            i += 1
        else:
            cost = estimate_tokens(lines[j]) + 1
            if cost > budget:
                break
            tail_lines.insert(0, lines[j])
            budget -= cost
            j -= 1
        take_head = not take_head
    return "\n".join(head_lines + ["…[上下文过长，已省略中段]…"] + tail_lines)


def fit_messages(
    messages: list[dict],
    *,
    window: int,
    reserve_output: int,
    soft_budget_ratio: float = 0.5,
) -> list[dict]:
    """按预算裁剪 messages，返回新列表（不就地修改入参元素）。

    规则：
      - 预算 = min(window - reserve_output, window * soft_budget_ratio)（软约束，控成本/延迟）；
      - 第 0 条 system 与最后一条 user 固定保留；
      - 历史从最旧往前裁，直到总量落入预算；
      - 触发裁剪记一条 INFO 日志。
    """
    if not messages:
        return messages
    hard_budget = max(1, int(window) - int(reserve_output))
    soft_budget = int(window * soft_budget_ratio) if soft_budget_ratio > 0 else hard_budget
    budget = min(hard_budget, soft_budget) if soft_budget > 0 else hard_budget

    total = sum(_message_tokens(m) for m in messages)
    if total <= budget:
        return list(messages)

    system_msgs = [m for m in messages if m.get("role") == "system"]
    last_user_idx = None
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].get("role") == "user":
            last_user_idx = idx
            break

    fixed_indices = set(id(m) for m in system_msgs)
    if last_user_idx is not None:
        fixed_indices.add(id(messages[last_user_idx]))

    middle = [m for m in messages if id(m) not in fixed_indices]
    fixed_tokens = sum(
        _message_tokens(m) for m in messages if id(m) in fixed_indices
    )

    kept_middle: list[dict] = []
    running = fixed_tokens
    for m in reversed(middle):
        cost = _message_tokens(m)
        if running + cost > budget:
            continue
        kept_middle.insert(0, m)
        running += cost

    dropped = len(middle) - len(kept_middle)
    kept_ids = set(id(m) for m in kept_middle)
    result: list[dict] = []
    for m in messages:
        if id(m) in fixed_indices or id(m) in kept_ids:
            result.append(m)

    if dropped > 0:
        logger.info(
            "上下文预算裁剪：窗口=%d 预算=%d 原始≈%d tokens，丢弃最旧 %d 条历史",
            window,
            budget,
            total,
            dropped,
        )
    return result


def should_summarize(
    messages: list[dict],
    *,
    window: int,
    reserve_output: int,
    trigger_ratio: float,
) -> bool:
    """判断历史是否已逼近窗口、需要压缩摘要（Phase 6）。

    触发阈值 = (window - reserve_output) * trigger_ratio；当全部 messages 估算
    token 超过该阈值时返回 True。trigger_ratio<=0 关闭该机制。
    """
    if trigger_ratio <= 0 or not messages:
        return False
    usable = max(1, int(window) - int(reserve_output))
    threshold = usable * float(trigger_ratio)
    total = sum(_message_tokens(m) for m in messages)
    return total > threshold
