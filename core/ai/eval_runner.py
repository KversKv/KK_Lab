"""AI eval 回归执行器（AI_Assistant_MD §2.7.2 / Phase 5a + P7）。

读 tests/ai_eval/cases/*.json（输入 + 期望行为），逐条用当前 prompt+nudges 配置跑，
断言期望命中；输出汇总 + 失败明细；返回非零退出码供 CI/脚本判断。

两种模式：
  - 真模型：连网调 NewAPIClient.chat（默认，需配置 base_url / API Key）；
  - mock 离线（--mock）：不连网，仅校验 messages 拼装/裁剪不报错，关键字断言跳过。

命令行：
  python -m core.ai.eval_runner          # 真模型
  python -m core.ai.eval_runner --mock   # 离线
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field

from log_config import get_logger

logger = get_logger(__name__)

_CASES_REL = ("tests", "ai_eval", "cases")


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cases_dir() -> str:
    return os.path.join(_project_root(), *_CASES_REL)


@dataclass
class EvalCase:
    id: str
    desc: str = ""
    page_key: str | None = None
    user: str = ""
    history: list[dict] = field(default_factory=list)
    expect: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    detail: str = ""


def load_cases(directory: str | None = None) -> list[EvalCase]:
    """读取回归用例目录下的所有 *.json；损坏文件跳过并记日志。"""
    directory = directory or cases_dir()
    cases: list[EvalCase] = []
    if not os.path.isdir(directory):
        logger.warning("eval 用例目录不存在: %s", directory)
        return cases
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            logger.error("读取 eval 用例失败: %s", path, exc_info=True)
            continue
        cases.append(
            EvalCase(
                id=str(data.get("id") or name[:-5]),
                desc=str(data.get("desc") or ""),
                page_key=data.get("page_key"),
                user=str(data.get("user") or ""),
                history=list(data.get("history") or []),
                expect=dict(data.get("expect") or {}),
            )
        )
    return cases


def _check_expect(content: str, tool_called: bool, expect: dict) -> tuple[bool, str]:
    """对模型结果做断言，返回 (通过, 失败原因)。"""
    if expect.get("expect_tool") is True and not tool_called:
        return False, "期望发起工具调用，但模型未调用任何工具"
    if expect.get("expect_tool") is False and tool_called:
        return False, "期望不调用工具，但模型发起了工具调用"

    text = content or ""
    all_kw = expect.get("all_keywords") or []
    missing = [kw for kw in all_kw if kw not in text]
    if missing:
        return False, f"缺少必须关键字: {missing}"

    any_kw = expect.get("any_keywords") or []
    if any_kw and not any(kw in text for kw in any_kw):
        return False, f"未命中任一关键字: {any_kw}"

    forbid_kw = expect.get("forbid_keywords") or []
    hit = [kw for kw in forbid_kw if kw in text]
    if hit:
        return False, f"出现被禁止关键字: {hit}"

    return True, ""


def run_case(case: EvalCase, *, mock: bool = False) -> EvalResult:
    """跑单条用例：拼装 messages → 调模型/mock → 断言。"""
    from core.ai.config import AISettings
    from core.ai.profiles import get_profile
    from core.ai.prompt_manager import BudgetConfig, PromptManager

    settings = AISettings.load()
    pm = PromptManager(enable_log_masking=settings.enable_log_masking)
    profile = get_profile(case.page_key)
    model = profile.get("model", settings.effective_model)
    window = settings.context_window_for(model)
    budget = BudgetConfig(
        window=window,
        reserve_output=settings.reserve_output_tokens,
        soft_budget_ratio=settings.soft_budget_ratio,
        max_context_block_tokens=settings.max_context_block_tokens,
    )
    try:
        messages = pm.build_messages(
            page_key=case.page_key,
            history=case.history,
            user_text=case.user,
            budget=budget,
        )
    except Exception as exc:  # noqa: BLE001 - 拼装失败即用例失败
        logger.error("用例 %s 拼装 messages 失败", case.id, exc_info=True)
        return EvalResult(case.id, False, f"拼装失败: {exc}")

    if mock:
        return EvalResult(case.id, True, "mock：拼装成功（跳过模型断言）")

    if not settings.is_configured():
        return EvalResult(case.id, False, "AI 未配置（缺 base_url / API Key），无法跑真模型")

    from core.ai.newapi_client import AIClientError, NewAPIClient

    client = NewAPIClient(
        base_url=settings.effective_base_url,
        api_key=settings.effective_api_key,
        timeout_seconds=settings.timeout_seconds,
    )
    tools = None
    expect_tool = case.expect.get("expect_tool")
    if expect_tool is True:
        try:
            from core.ai.actions.builder import build_registry

            tools = build_registry().to_tools() or None
        except Exception:
            logger.info("用例 %s 构建 tools 失败，按无工具跑", case.id, exc_info=True)
            tools = None
    try:
        result = client.chat(
            model=model,
            messages=messages,
            temperature=profile.get("temperature", 0.1),
            max_tokens=profile.get("max_tokens", 2048),
            tools=tools,
        )
    except AIClientError as exc:
        return EvalResult(case.id, False, f"模型调用失败: {exc}")
    tool_called = bool(getattr(result, "tool_calls", None))
    passed, detail = _check_expect(result.content, tool_called, case.expect)
    return EvalResult(case.id, passed, detail)


def run_all(*, mock: bool = False, directory: str | None = None) -> list[EvalResult]:
    cases = load_cases(directory)
    results: list[EvalResult] = []
    for case in cases:
        results.append(run_case(case, mock=mock))
    return results


def summarize(results: list[EvalResult]) -> tuple[int, int]:
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    return passed, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI eval 回归执行器")
    parser.add_argument(
        "--mock", action="store_true", help="离线 mock：仅校验拼装，不连模型"
    )
    parser.add_argument("--dir", default=None, help="自定义用例目录")
    args = parser.parse_args(argv)

    results = run_all(mock=args.mock, directory=args.dir)
    passed, failed = summarize(results)
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        line = f"[{flag}] {r.case_id}"
        if r.detail:
            line += f"  - {r.detail}"
        logger.info(line)
        print(line)
    summary = f"\n通过 {passed} / 失败 {failed}（共 {len(results)}）"
    logger.info(summary)
    print(summary)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
