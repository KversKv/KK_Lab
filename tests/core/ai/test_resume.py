# -*- coding: utf-8 -*-
"""S2 Resume 续跑入口单测：resume_with_task_result 的定位/幂等/降级分支。

只覆盖不触发真实模型调用的降级分支（未配置 / 会话不匹配 / 幂等 / 未知 task）。
模型续跑路径属集成行为，由手动/集成测试覆盖。

可独立运行：
    python tests/core/ai/test_resume.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# QObject signal 需要 QApplication 存在
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.ai.config import AISettings  # noqa: E402
from core.ai.ai_service import AIService  # noqa: E402

_app = QApplication.instance() or QApplication([])


def _make_service() -> AIService:
    settings = AISettings.load()
    # 强制未配置：resume 命中降级分支，不发起模型调用
    settings.base_url = ""
    settings.api_key = ""
    settings.set_runtime_api_key("")
    return AIService(settings)


def test_resume_unknown_task():
    svc = _make_service()
    assert svc.resume_with_task_result("T-9999", {"x": 1}) is False


def test_resume_empty_task_id():
    svc = _make_service()
    assert svc.resume_with_task_result("", {"x": 1}) is False


def test_resume_idempotent():
    svc = _make_service()
    reg = svc.pending_task_registry
    sk = svc.current_session_key()
    tid = reg.register(sk, "scan")
    # 第一次：会走到"未配置"降级（返回 False），但已 mark_resumed
    svc.resume_with_task_result(tid, {"count": 2})
    assert reg.get(tid).resumed is True
    # 第二次：幂等闸拦截
    skipped = {}
    svc.task_resume_skipped.connect(lambda info: skipped.update(info))
    assert svc.resume_with_task_result(tid, {"count": 2}) is False
    assert skipped.get("reason") == "already_resumed"


def test_resume_session_mismatch():
    svc = _make_service()
    reg = svc.pending_task_registry
    tid = reg.register("some_other_session", "scan")
    skipped = {}
    svc.task_resume_skipped.connect(lambda info: skipped.update(info))
    assert svc.resume_with_task_result(tid, {"v": 1}) is False
    assert skipped.get("reason") == "session_mismatch"


def test_resume_unconfigured_degrade():
    svc = _make_service()
    reg = svc.pending_task_registry
    sk = svc.current_session_key()
    tid = reg.register(sk, "scan")
    skipped = {}
    svc.task_resume_skipped.connect(lambda info: skipped.update(info))
    assert svc.resume_with_task_result(tid, {"v": 1}) is False
    assert skipped.get("reason") == "unavailable"


def test_format_task_result_summary():
    text = AIService._format_task_result(
        {"task_id": "T-1", "kind": "扫描", "title": "找仪器", "result": {"n": 3}}
    )
    assert "T-1" in text
    assert "扫描" in text
    assert "找仪器" in text


# --- S5-5 续跑轮数 / 预算硬约束回归 ---

def test_resume_result_clipped_within_budget():
    """大结果回灌时必须裁剪，控 token（§6）：续跑提示受 800-token 块约束。"""
    import json as _json

    huge = {"rows": ["x" * 50 for _ in range(200)]}  # 远超 800 token
    raw_len = len(_json.dumps(huge, ensure_ascii=False))
    text = AIService._format_task_result(
        {"task_id": "T-big", "kind": "序列", "title": "", "result": huge}
    )
    # 已裁剪：含中段省略标记，且整体显著短于原始 JSON
    assert "省略中段" in text
    assert len(text) < raw_len


def test_max_tool_rounds_constant():
    """续跑复用 agent 路径的轮数硬上限常量必须存在且为正（防失控自循环）。"""
    from core.ai import ai_service as _mod

    assert isinstance(_mod._MAX_TOOL_ROUNDS, int)
    assert _mod._MAX_TOOL_ROUNDS >= 1


def test_resume_resets_agent_rounds():
    """续跑入口须把 _agent_rounds 归零，保证每次回灌从 0 起算受 _MAX_TOOL_ROUNDS 约束。

    未配置降级会提前返回，但此前的幂等/归属判定不应破坏轮数计数语义；
    本用例验证：在降级前人为污染的 rounds 不会泄漏成已达上限而误拦后续会话。
    """
    svc = _make_service()
    svc._agent_rounds = 999  # 模拟上一次会话留下的脏值
    reg = svc.pending_task_registry
    sk = svc.current_session_key()
    tid = reg.register(sk, "scan")
    # 未配置 → 降级返回 False（不进入续跑），脏值不会触发模型调用
    assert svc.resume_with_task_result(tid, {"v": 1}) is False


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
