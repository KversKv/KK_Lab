"""自定义测试执行引擎"""

from __future__ import annotations

import time
import traceback
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode
from ui.pages.custom_test.context import (
    ExecutionContext, BreakLoop, ContinueLoop, StopExecution, TestResultException,
)

logger = get_logger(__name__)


def _decimal_places(v: float) -> int:
    s = f"{v:.12g}"
    if "." in s:
        return len(s.split(".")[1].rstrip("0")) or 0
    return 0


class _ColumnFormatter:
    __slots__ = ("_col_dp",)

    def __init__(self) -> None:
        self._col_dp: Dict[str, int] = {}

    def format_row(self, row: dict) -> dict:
        for k, v in row.items():
            if isinstance(v, float):
                dp = max(2, min(_decimal_places(v), 10))
                if dp > self._col_dp.get(k, 2):
                    self._col_dp[k] = dp
        return {
            k: f"{v:.{self._col_dp.get(k, 2)}f}" if isinstance(v, float) else v
            for k, v in row.items()
        }

    def get_dp(self, key: str) -> int:
        return self._col_dp.get(key, 2)


def _execute_children(children: List[BaseNode], context: ExecutionContext) -> None:
    """深度优先执行子节点列表"""
    for child in children:
        if context.should_stop:
            return
        while context.should_pause and not context.should_stop:
            time.sleep(0.1)
        try:
            _execute_node(child, context)
        except ContinueLoop:
            return
        except BreakLoop:
            raise


def _execute_node(node: BaseNode, context: ExecutionContext) -> None:
    """执行单个节点，触发上下文回调"""
    if context.on_step_started:
        context.on_step_started(node.uid, node.display_name)
    node.execute(context)
    if context.on_step_finished:
        context.on_step_finished(node.uid, node.display_name)


class CustomTestExecutor(QObject):
    """自定义测试执行器（在工作线程中运行）"""

    step_started = Signal(str, str)
    step_finished = Signal(str, str)
    data_recorded = Signal(dict)
    progress_updated = Signal(int, int)
    log_message = Signal(str)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._sequence: List[BaseNode] = []
        self._context: Optional[ExecutionContext] = None

    def set_sequence(self, nodes: List[BaseNode]) -> None:
        """设置待执行的节点序列"""
        self._sequence = nodes

    def set_context(self, context: ExecutionContext) -> None:
        """设置执行上下文"""
        self._context = context

    @property
    def context(self) -> Optional[ExecutionContext]:
        return self._context

    def request_stop(self) -> None:
        """请求停止"""
        if self._context:
            self._context.request_stop()

    def request_pause(self) -> None:
        """请求暂停"""
        if self._context:
            self._context.request_pause()

    def request_resume(self) -> None:
        """恢复执行"""
        if self._context:
            self._context.request_resume()

    def run(self) -> None:
        """主执行入口"""
        if not self._context:
            self.error.emit("执行上下文未初始化")
            self.finished.emit(False, "执行上下文未初始化")
            return

        if not self._sequence:
            self.log_message.emit("[WARN] 序列为空，无需执行")
            self.finished.emit(True, "序列为空")
            return

        total_steps = self._count_steps(self._sequence)
        executed = [0]

        original_record = self._context.record_data

        def _hooked_record(row: Dict[str, Any]) -> None:
            original_record(row)
            self.data_recorded.emit(dict(row))

        self._context.record_data = _hooked_record

        original_log_output = self._context.log_output

        def _hooked_log_output(message: str) -> None:
            original_log_output(message)
            self.log_message.emit(message)

        self._context.log_output = _hooked_log_output

        def _hooked_step_started(uid: str, name: str) -> None:
            self.step_started.emit(uid, name)
            self.log_message.emit(f"[STEP] {name} (uid={uid[:8]})")

        def _hooked_step_finished(uid: str, name: str) -> None:
            self.step_finished.emit(uid, name)

        self._context.on_step_started = _hooked_step_started
        self._context.on_step_finished = _hooked_step_finished

        self.log_message.emit(f"[START] 开始执行序列，共 {total_steps} 个步骤")
        col_fmt = _ColumnFormatter()

        try:
            self._run_nodes(self._sequence, total_steps, executed, col_fmt)

            if self._context.should_stop:
                self.log_message.emit("[STOP] 执行被用户中止")
                self.finished.emit(False, "用户中止")
            elif self._context._test_passed is not None:
                if self._context._test_passed:
                    self.log_message.emit(f"[PASS] 测试通过 — {self._context._test_message}")
                    self.finished.emit(True, f"测试通过: {self._context._test_message}")
                else:
                    self.log_message.emit(f"[FAIL] 测试失败 — {self._context._test_message}")
                    self.finished.emit(False, f"测试失败: {self._context._test_message}")
            else:
                self.log_message.emit(f"[DONE] 执行完成，记录 {len(self._context.records)} 行数据")
                self.finished.emit(True, "执行完成")
        except StopExecution as e:
            self.log_message.emit(f"[STOP] {e.message or '执行已停止'}")
            self.finished.emit(False, e.message or "执行已停止")
        except TestResultException as e:
            if e.passed:
                self.log_message.emit(f"[PASS] {e.message}")
                self.finished.emit(True, f"测试通过: {e.message}")
            else:
                self.log_message.emit(f"[FAIL] {e.message}")
                self.finished.emit(False, f"测试失败: {e.message}")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("执行异常: %s\n%s", e, tb)
            self.log_message.emit(f"[ERROR] {e}")
            self.error.emit(str(e))
            self.finished.emit(False, str(e))

    def _run_nodes(self, nodes: List[BaseNode], total: int, executed: List[int], col_fmt: _ColumnFormatter) -> None:
        for node in nodes:
            if self._context.should_stop:
                return
            while self._context.should_pause and not self._context.should_stop:
                time.sleep(0.1)

            pre_record_count = len(self._context.records)

            try:
                _execute_node(node, self._context)
            except Exception as e:
                self.log_message.emit(f"[ERROR] {node.display_name}: {e}")
                raise

            executed[0] += 1
            self.progress_updated.emit(executed[0], total)

            new_records = self._context.records[pre_record_count:]
            for rec in new_records:
                formatted = col_fmt.format_row(rec)
                self.log_message.emit(f"[DATA] {formatted}")

    def _count_steps(self, nodes: List[BaseNode]) -> int:
        """统计非容器节点的总步骤数"""
        count = 0
        for node in nodes:
            count += 1
            if node.children:
                count += self._count_steps(node.children)
        return count


class ExecutorThread(QObject):
    """封装 QThread + Executor 的便捷类"""

    finished = Signal(bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._executor: Optional[CustomTestExecutor] = None

    @property
    def executor(self) -> Optional[CustomTestExecutor]:
        return self._executor

    def start(self, nodes: List[BaseNode], context: ExecutionContext) -> CustomTestExecutor:
        """启动执行"""
        self.stop()

        self._executor = CustomTestExecutor()
        self._executor.set_sequence(nodes)
        self._executor.set_context(context)

        self._thread = QThread()
        self._executor.moveToThread(self._thread)

        self._thread.started.connect(self._executor.run)
        self._executor.finished.connect(self._on_finished)
        self._executor.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

        self._thread.start()
        return self._executor

    def stop(self) -> None:
        """停止执行"""
        if self._executor:
            self._executor.request_stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)

    def _on_finished(self, success: bool, message: str) -> None:
        self.finished.emit(success, message)

    def _cleanup(self) -> None:
        if self._executor:
            self._executor.deleteLater()
            self._executor = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
