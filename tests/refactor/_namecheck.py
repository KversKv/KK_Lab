#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量未定义名称检查器（重构期安全网）。

无 ruff/pyflakes 环境下，用于检查 mixin 文件里方法体引用了
但既未导入也未在模块/局部作用域定义的名字（典型漏 import 场景）。

用法：
    python tests/refactor/_namecheck.py <file.py> [<file.py> ...]

仅作近似检查：报告 Load 上下文中"看起来未定义"的名字。
"""

import ast
import builtins
import sys


_BUILTINS = set(dir(builtins)) | {"__name__", "__file__", "__package__"}


def _target_names(target):
    names = []
    if isinstance(target, ast.Name):
        names.append(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.extend(_target_names(elt))
    elif isinstance(target, ast.Starred):
        names.extend(_target_names(target.value))
    elif isinstance(target, ast.Attribute):
        pass
    return names


class _Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.names = set()

    def define(self, name):
        self.names.add(name)

    def is_local(self, name):
        s = self
        while s is not None:
            if name in s.names:
                return True
            s = s.parent
        return False


class _Checker(ast.NodeVisitor):
    def __init__(self, module_names):
        self.module_names = module_names
        self.scope = _Scope()
        self.undefined = []
        self._func_depth = 0

    def _push(self):
        self.scope = _Scope(self.scope)

    def _pop(self):
        self.scope = self.scope.parent

    def _record(self, name, node):
        if (
            name not in self.module_names
            and not self.scope.is_local(name)
            and name not in _BUILTINS
            and name not in ("self", "cls")
        ):
            self.undefined.append((node.lineno, name))

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self._record(node.id, node)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.scope.define(node.id)
        self.generic_visit(node)

    def visit_Arg(self, node):
        self.scope.define(node.arg)
        if node.annotation is not None:
            self.visit(node.annotation)

    def visit_arguments(self, node):
        for a in node.posonlyargs + node.args + node.kwonlyargs:
            self.scope.define(a.arg)
        if node.vararg:
            self.scope.define(node.vararg.arg)
        if node.kwarg:
            self.scope.define(node.kwarg.arg)
        for d in node.defaults + node.kw_defaults:
            if d is not None:
                self.visit(d)

    def _bind_args(self, args):
        self.visit_arguments(args)

    def visit_FunctionDef(self, node):
        self.scope.define(node.name)
        for d in node.decorator_list:
            self.visit(d)
        self._push()
        self._func_depth += 1
        self._bind_args(node.args)
        for a in node.returns, :
            if a is not None:
                self.visit(a)
        for stmt in node.body:
            self.visit(stmt)
        self._func_depth -= 1
        self._pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self._push()
        self._bind_args(node.args)
        self.visit(node.body)
        self._pop()

    def visit_ClassDef(self, node):
        self.scope.define(node.name)
        for d in node.decorator_list:
            self.visit(d)
        for b in node.bases:
            self.visit(b)
        self._push()
        for stmt in node.body:
            self.visit(stmt)
        self._pop()

    def visit_Assign(self, node):
        for t in node.targets:
            for n in _target_names(t):
                self.scope.define(n)
            self.visit(t)
        self.visit(node.value)

    def visit_AnnAssign(self, node):
        if node.target is not None and isinstance(node.target, ast.Name):
            self.scope.define(node.target.id)
        if node.value is not None:
            self.visit(node.value)
        if node.annotation is not None:
            self.visit(node.annotation)

    def visit_AugAssign(self, node):
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node):
        for n in _target_names(node.target):
            self.scope.define(n)
        self.visit(node.target)
        self.visit(node.iter)
        for s in node.body:
            self.visit(s)
        for s in node.orelse:
            self.visit(s)

    visit_AsyncFor = visit_For

    def visit_With(self, node):
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                for n in _target_names(item.optional_vars):
                    self.scope.define(n)
                self.visit(item.optional_vars)
        for s in node.body:
            self.visit(s)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node):
        if node.name:
            self.scope.define(node.name)
        self.visit(node.type)
        for s in node.body:
            self.visit(s)

    def visit_Import(self, node):
        for alias in node.names:
            self.scope.define(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            self.scope.define(alias.asname or alias.name)

    def visit_comprehension(self, node):
        for n in _target_names(node.target):
            self.scope.define(n)
        self.visit(node.target)
        self.visit(node.iter)
        for if_ in node.ifs:
            self.visit(if_)

    def visit_ListComp(self, node):
        self._push()
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        self._pop()

    visit_SetComp = visit_ListComp

    def visit_DictComp(self, node):
        self._push()
        for g in node.generators:
            self.visit(g)
        self.visit(node.key)
        self.visit(node.value)
        self._pop()

    def visit_GeneratorExp(self, node):
        self._push()
        for g in node.generators:
            self.visit(g)
        self.visit(node.elt)
        self._pop()

    def visit_Global(self, node):
        for n in node.names:
            self.scope.define(n)

    visit_Nonlocal = visit_Global

    def visit_NamedExpr(self, node):
        for n in _target_names(node.target):
            self.scope.define(n)
        self.visit(node.value)


def _module_level_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    names.add(a.asname or a.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                names.update(_target_names(t))
        elif isinstance(node, ast.AnnAssign):
            names.update(_target_names(node.target))
        elif isinstance(node, ast.If):
            for n in _collect_if_names(node):
                names.add(n)
    return names


def _collect_if_names(node):
    out = []
    for stmt in node.body + node.orelse:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                out.extend(_target_names(t))
        elif isinstance(stmt, ast.AnnAssign):
            out.extend(_target_names(stmt.target))
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(stmt.name)
        elif isinstance(stmt, ast.Import):
            for a in stmt.names:
                out.append(a.asname or a.name.split(".")[0])
        elif isinstance(stmt, ast.ImportFrom):
            for a in stmt.names:
                if a.name != "*":
                    out.append(a.asname or a.name)
    return out


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    mod_names = _module_level_names(tree)
    checker = _Checker(mod_names)
    for node in tree.body:
        checker.visit(node)
    return checker.undefined


def main(argv):
    bad = False
    for path in argv[1:]:
        undef = check_file(path)
        if undef:
            bad = True
            print(f"[UNDEFINED] {path}")
            seen = set()
            for lineno, name in undef:
                key = name
                if key in seen:
                    continue
                seen.add(key)
                print(f"    line {lineno}: {name}")
        else:
            print(f"[OK] {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
