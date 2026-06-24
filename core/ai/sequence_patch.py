"""序列 Patch 模型 + 应用器（F5.2）。

AI 优化 Orchestrator 序列有两种回报：
  - 完整序列（短序列最稳）：由 ScriptDraft 走完整往返；
  - 结构化 patch（长序列省 token、diff 清晰）：由本模块定义并应用于 v2 dict。

Patch 作用于"序列 dict"（{version, sequence, instruments, metadata}）的 sequence 树，
通过 path（顶层从 0 开始的索引链，进入容器节点 children）定位目标，支持三类操作：
  - insert：在 path 指向的列表位置插入一个新节点；
  - delete：删除 path 指向的节点；
  - edit  ：合并更新 path 指向节点的 params（浅合并，值为 null 表示删除该参数）。

应用是"非破坏"的：在输入 dict 的深拷贝上操作，返回新 dict + issues，调用方负责
再走 serialization 反序列化 + preflight 校验。

本模块纯逻辑，禁 import Qt，不引入额外依赖。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from log_config import get_logger

logger = get_logger(__name__)

OP_INSERT = "insert"
OP_DELETE = "delete"
OP_EDIT = "edit"
PATCH_OPS = (OP_INSERT, OP_DELETE, OP_EDIT)


@dataclass(frozen=True)
class PatchIssue:
    severity: str
    message: str
    op: str = ""

    def format(self) -> str:
        prefix = f"[{self.severity.upper()}]"
        location = f"({self.op})" if self.op else ""
        return f"{prefix} patch{location}: {self.message}"


@dataclass
class PatchOp:
    """单条 patch 操作。

    op   : insert / delete / edit；
    path : 顶层从 0 开始的索引链，逐级进入容器节点的 children，例如 [1, 0]；
    node : insert 时的新节点 dict（含 node_type/params/children?）；
    params: edit 时要合并的参数（值为 None 表示删除该参数键）。
    """

    op: str
    path: list[int] = field(default_factory=list)
    node: dict[str, Any] | None = None
    params: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatchOp":
        raw_path = data.get("path", [])
        path: list[int] = []
        if isinstance(raw_path, list):
            for item in raw_path:
                try:
                    path.append(int(item))
                except (TypeError, ValueError):
                    continue
        node = data.get("node")
        if not isinstance(node, dict):
            node = None
        params = data.get("params")
        if not isinstance(params, dict):
            params = None
        return cls(
            op=str(data.get("op", "")).lower(),
            path=path,
            node=node,
            params=params,
        )


@dataclass
class SequencePatch:
    """一组有序 patch 操作。"""

    ops: list[PatchOp] = field(default_factory=list)
    title: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SequencePatch":
        raw_ops = data.get("ops", [])
        ops: list[PatchOp] = []
        if isinstance(raw_ops, list):
            for item in raw_ops:
                if isinstance(item, dict):
                    ops.append(PatchOp.from_dict(item))
        return cls(
            ops=ops,
            title=str(data.get("title", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class PatchApplyResult:
    """patch 应用结果：新序列 dict + issues。"""

    sequence_data: dict[str, Any]
    issues: list[PatchIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[PatchIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def _children_list(node: dict[str, Any]) -> list[Any]:
    children = node.get("children")
    if not isinstance(children, list):
        children = []
        node["children"] = children
    return children


def _resolve_parent_list(
    sequence: list[Any], path: list[int]
) -> tuple[list[Any] | None, int, str]:
    """按 path 定位目标所在的父列表与目标索引。

    返回 (parent_list, index, error)；error 非空表示定位失败。
    末级索引为目标自身在父列表中的位置（insert 允许等于 len）。
    """
    if not path:
        return None, -1, "path 不能为空。"
    current = sequence
    for depth, raw_index in enumerate(path[:-1]):
        if not isinstance(current, list):
            return None, -1, f"path 第 {depth} 级不是列表。"
        if raw_index < 0 or raw_index >= len(current):
            return None, -1, f"path 第 {depth} 级索引越界：{raw_index}。"
        node = current[raw_index]
        if not isinstance(node, dict):
            return None, -1, f"path 第 {depth} 级目标不是节点。"
        current = _children_list(node)
    if not isinstance(current, list):
        return None, -1, "目标父级不是列表。"
    return current, path[-1], ""


def apply_patch(sequence_data: dict[str, Any], patch: SequencePatch) -> PatchApplyResult:
    """在 sequence_data 深拷贝上顺序应用 patch，返回新 dict + issues。

    删除/编辑使用同一批 path 时按操作给定顺序执行；调用方应保证 path 语义一致
    （建议同一批 patch 内删除从后往前、或一次只针对一个目标）。
    """
    new_data = copy.deepcopy(sequence_data) if isinstance(sequence_data, dict) else {}
    sequence = new_data.get("sequence")
    if not isinstance(sequence, list):
        sequence = []
        new_data["sequence"] = sequence

    issues: list[PatchIssue] = []
    if not patch.ops:
        issues.append(PatchIssue("warning", "patch 不含任何操作。"))
        return PatchApplyResult(new_data, issues)

    for op in patch.ops:
        if op.op not in PATCH_OPS:
            issues.append(PatchIssue("error", f"未知操作：{op.op or '(空)'}", op=op.op))
            continue
        parent, index, err = _resolve_parent_list(sequence, op.path)
        if err or parent is None:
            issues.append(PatchIssue("error", err or "定位失败。", op=op.op))
            continue

        if op.op == OP_INSERT:
            if not isinstance(op.node, dict) or not op.node.get("node_type"):
                issues.append(PatchIssue("error", "insert 缺少有效 node（需含 node_type）。", op=op.op))
                continue
            if index < 0 or index > len(parent):
                issues.append(PatchIssue("error", f"insert 索引越界：{index}。", op=op.op))
                continue
            parent.insert(index, copy.deepcopy(op.node))

        elif op.op == OP_DELETE:
            if index < 0 or index >= len(parent):
                issues.append(PatchIssue("error", f"delete 索引越界：{index}。", op=op.op))
                continue
            parent.pop(index)

        elif op.op == OP_EDIT:
            if index < 0 or index >= len(parent):
                issues.append(PatchIssue("error", f"edit 索引越界：{index}。", op=op.op))
                continue
            target = parent[index]
            if not isinstance(target, dict):
                issues.append(PatchIssue("error", "edit 目标不是节点。", op=op.op))
                continue
            if not op.params:
                issues.append(PatchIssue("warning", "edit 未提供 params，跳过。", op=op.op))
                continue
            params = target.get("params")
            if not isinstance(params, dict):
                params = {}
                target["params"] = params
            for key, value in op.params.items():
                if value is None:
                    params.pop(key, None)
                else:
                    params[key] = value

    return PatchApplyResult(new_data, issues)
