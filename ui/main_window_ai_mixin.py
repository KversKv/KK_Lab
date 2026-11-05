# -*- coding: utf-8 -*-

from PySide6.QtCore import QEventLoop, Qt, QTimer

from core.ai.log_ring import get_log_ring
from core.ai.page_contract import (
    CAP_APPLY_CONFIG,
    CAP_GET_CONFIG,
    CAP_GET_RESULT,
    CAP_START_TEST,
    CAP_STOP_TEST,
)
from core.ai.ui_action_registry import UIActionRegistry
from log_config import get_logger

logger = get_logger(__name__)


def _ai_caps(page) -> set[str]:
    """安全获取页面的 AI 能力集（未实现 ai_capabilities 返回空集）。

    鸭子类型：页面不强制继承 AIControllablePage，只要实现 ai_capabilities() 即可。
    """
    getter = getattr(page, "ai_capabilities", None)
    if not callable(getter):
        return set()
    try:
        return set(getter())
    except Exception:  # noqa: BLE001 - 能力查询失败不致命，降级为空集
        logger.error("获取页面 AI 能力集失败", exc_info=True)
        return set()


class MainWindowAiMixin:
    def _setup_ai_action_system(self):
        from core.ai.actions import ActionDeps, build_action_system

        # §5b：UI 动作注册表（页面声明式白名单，供 list_ui_actions/ui_invoke）
        self._ui_action_registry = UIActionRegistry()

        deps = ActionDeps(
            instrument_manager=self.instrument_manager,
            page_key_getter=self._get_ai_page_key,
            serial_status_getter=self._get_ai_serial_status,
            serial_manager_getter=self._current_serial_manager,
            serial_ports_getter=self._ai_serial_list_ports,
            execution_logs_getter=self._get_ai_execution_logs,
            app_logs_getter=self._get_ai_app_logs,
            rx_recent_getter=self._get_ai_recent_rx,
            test_status_getter=self._get_ai_test_status,
            test_config_getter=self._get_ai_test_config,
            test_steps_getter=self._get_ai_test_steps,
            test_result_summary_getter=self._get_ai_test_result_summary,
            waveform_data_getter=self._provide_ai_waveform_windowed,
            waveform_full_data_getter=self._provide_ai_waveform_full,
            draft_registry=self.ai_service.draft_registry,
            artifact_registry=self.ai_service.artifact_registry,
            scheduled_task_registry=self.ai_service.scheduled_task_registry,
            pending_task_registry=self.ai_service.pending_task_registry,
            session_key_getter=self.ai_service.current_session_key,
            action_name_validator=self._ai_action_is_registered,
            schedule_register_callback=self._ai_schedule_register,
            open_page_callback=self._ai_open_page,
            toggle_ai_panel_callback=self._ai_toggle_panel,
            serial_send_text_callback=self._ai_serial_send_text,
            serial_clear_callback=self._ai_serial_clear,
            test_run_callback=self._ai_test_run,
            test_pause_callback=self._ai_test_pause,
            test_stop_callback=self._ai_test_stop,
            test_set_variable_callback=self._ai_test_set_variable,
            test_run_single_step_callback=self._ai_test_run_single_step,
            config_apply_callback=self._apply_ai_config_draft,
            script_apply_callback=self._apply_ai_script_draft,
            chamber_wait_stable_callback=self._ai_chamber_wait_stable,
            datalog_export_callback=self._ai_export_datalog_csv,
            ui_action_registry=self._ui_action_registry,
            ui_invoke_callback=self._ai_ui_invoke,
        )
        registry, dispatcher = build_action_system(
            deps,
            require_confirm_high=self.ai_settings.require_confirm_high_risk_action,
            allow_critical=False,
        )
        dispatcher.set_confirm_callback(self.ai_panel.confirm_action)
        self.ai_service.set_action_system(registry, dispatcher)
        # Phase 4.2：注入当前页 AI 能力集 getter，供 AIService 调
        # registry.to_tools(capabilities) 按页裁剪 tools（专项页只看到本页能干的事）。
        self.ai_service.set_page_capabilities_getter(
            lambda: _ai_caps(self.resolve_active_ai_page())
        )
        # 调度（§3/§4）：task_id -> QTimer，到点触发已登记的目标动作
        self._scheduled_timers: dict[str, QTimer] = {}
        # 异步动作回灌（§4 / S3）：扫描完成 → 找到对应 pending 任务并续跑
        try:
            self.instrument_manager.scan_finished.connect(
                self._ai_on_scan_finished_resume
            )
        except Exception:  # noqa: BLE001
            logger.error("连接 scan_finished 回灌信号失败", exc_info=True)

    def _ai_on_scan_finished_resume(self, instrument_type: str, candidates: list):
        """扫描完成 → 回灌对应 pending 任务，触发 AI 续跑（§4 / S3-1）。"""
        registry = self.ai_service.pending_task_registry
        session_key = self.ai_service.current_session_key()
        # 找最新一个未 resumed、kind=scan_instruments 且 title==type 的 pending 任务
        target = None
        for t in registry.list(session_key=session_key):
            if (
                t.get("kind") == "scan_instruments"
                and t.get("title") == instrument_type
                and not t.get("resumed")
            ):
                target = t
        if target is None:
            return
        count = len(candidates) if candidates else 0
        result = {
            "ok": True,
            "instrument_type": instrument_type,
            "count": count,
            "_message": f"扫描完成：找到 {count} 个 {instrument_type} 候选。",
        }
        self.ai_service.resume_with_task_result(
            target.get("task_id"), result, kind="scan_instruments", title=instrument_type
        )

    def _ai_action_is_registered(self, name: str) -> bool:
        """校验 schedule_action 的目标动作名是否已注册（§3.3）。"""
        registry = getattr(self.ai_service, "_registry", None)
        return bool(registry and registry.has(name))

    def _ai_schedule_register(self, task_id: str, delay_seconds: float):
        """UI 注入回调：登记成功后起一个单次 QTimer，到点执行目标动作（§3.4）。"""
        try:
            timer = QTimer(self)
            timer.setSingleShot(True)
            interval_ms = max(0, int(float(delay_seconds) * 1000))
            timer.timeout.connect(lambda tid=task_id: self._ai_fire_scheduled_task(tid))
            self._scheduled_timers[task_id] = timer
            timer.start(interval_ms)
            return True, f"已启动定时触发器：{task_id}"
        except Exception:  # noqa: BLE001
            logger.error("启动调度定时器失败：%s", task_id, exc_info=True)
            return False, "启动定时触发器失败。"

    def _ai_fire_scheduled_task(self, task_id: str):
        """QTimer 到点回调：经 dispatcher 执行目标动作并续跑回灌（§3.4/§4）。"""
        self._scheduled_timers.pop(task_id, None)
        registry = self.ai_service.scheduled_task_registry
        task = registry.mark_running(task_id)
        if task is None:
            logger.info("调度任务 %s 已取消或状态异常，跳过触发。", task_id)
            return
        dispatcher = self.ai_service.dispatcher
        if dispatcher is None:
            registry.mark_done(task_id, {"status": "failed"}, ok=False)
            return
        action = task.action or {}
        name = str(action.get("name", ""))
        arguments = action.get("arguments") or {}
        try:
            outcome = dispatcher.dispatch(
                name, arguments, bypass_confirmation=bool(task.pre_authorized)
            )
            result = outcome.to_tool_payload()
            ok = outcome.ok
        except Exception:  # noqa: BLE001
            logger.error("调度任务 %s 执行动作 %s 失败", task_id, name, exc_info=True)
            result = {"status": "failed", "message": "执行异常"}
            ok = False
        registry.mark_done(task_id, result, ok=ok)
        # 把调度结果作为一个 pending 任务回灌 AI 续跑（§4）
        pending = self.ai_service.pending_task_registry
        pid = pending.register(
            task.session_key, "scheduled", title=f"定时执行 {name}"
        )
        self.ai_service.resume_with_task_result(
            pid, result, kind="scheduled", title=f"定时执行 {name}"
        )

    def _ai_cancel_scheduled_timer(self, task_id: str):
        """取消调度任务时一并停掉 QTimer（配合 cancel_scheduled_task）。"""
        timer = self._scheduled_timers.pop(task_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _get_ai_app_logs(self, lines):
        ring = get_log_ring()
        if ring is None:
            return []
        return ring.recent(lines)

    def _get_ai_recent_rx(self, session_id, lines):
        service = getattr(self, "ai_service", None)
        if service is None:
            return []
        return service.rx_cache.recent(session_id, lines)

    def _get_ai_test_status(self):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return None
        canvas = getattr(ui, "canvas", None)
        running = bool(getattr(canvas, "_running", False)) if canvas else False
        steps = 0
        if canvas is not None:
            try:
                steps = len(canvas.get_sequence())
            except Exception:  # noqa: BLE001 - 状态查询失败不致命
                steps = 0
        return {"available": True, "running": running, "steps": steps}

    def _get_ai_test_config(self):
        page = self.resolve_active_ai_page()
        if page is None or CAP_GET_CONFIG not in _ai_caps(page):
            return None
        getter = getattr(page, "ai_get_config", None)
        if not callable(getter):
            return None
        try:
            return getter()
        except Exception:  # noqa: BLE001 - 快照失败不致命
            logger.error("AI 获取测试配置失败", exc_info=True)
            return None

    def _get_ai_test_steps(self):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return None
        getter = getattr(ui, "get_ai_test_steps", None)
        if not callable(getter):
            return None
        return getter()

    def _get_ai_test_result_summary(self):
        page = self.resolve_active_ai_page()
        if page is None or CAP_GET_RESULT not in _ai_caps(page):
            return None
        getter = getattr(page, "ai_get_result_summary", None)
        if not callable(getter):
            return None
        try:
            return getter()
        except Exception:  # noqa: BLE001 - 摘要查询失败不致命
            logger.error("AI 获取测试结果摘要失败", exc_info=True)
            return None

    def _ai_test_set_variable(self, name, value):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return False, "请先切换到 Orchestrator 页面。"
        setter = getattr(ui, "ai_set_test_variable", None)
        if not callable(setter):
            return False, "当前页面不支持设置测试变量。"
        try:
            return setter(name, value)
        except Exception:  # noqa: BLE001 - 设置异常转可读结果
            logger.error("AI 设置测试变量失败", exc_info=True)
            return False, "设置变量异常，请查看日志。"

    def _ai_test_run_single_step(self, step_id):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return False, "请先切换到 Orchestrator 页面。"
        runner = getattr(ui, "ai_run_single_step", None)
        if not callable(runner):
            return False, "当前页面不支持单步执行。"
        try:
            return runner(step_id)
        except Exception:  # noqa: BLE001 - 单步异常转可读结果
            logger.error("AI 单步执行失败", exc_info=True)
            return False, "单步执行异常，请查看日志。"

    def _ai_open_page(self, page):
        button_map = {
            "power_analyser": self.nav.n6705c_power_analyzer_btn,
            "datalog": self.nav.n6705c_power_analyzer_btn,
            "oscilloscope": self.nav.oscilloscope_btn,
            "thermal_chamber": self.nav.chamber_btn,
            "pmu_test": self.nav.pmu_test_btn,
            "charger_test": self.nav.charger_test_btn,
            "consumption_test": self.nav.consumption_test_btn,
            "vmin_hunter": self.nav.vmin_hunter_btn,
            "vmin_single_test": self.nav.vmin_hunter_btn,
            "orchestrator": self.nav.orchestrator_btn,
            "kk_serials": self.nav.collection_btn,
            "i2c_control": self.nav.collection_btn,
            "collection": self.nav.collection_btn,
            "pmu_1811": self.nav.pmu_btn,
            "pmu_1860": self.nav.pmu_btn,
        }
        # Collection 子项：先选定子项再点击父按钮，确保跳转到目标子页
        _collection_subkeys = {
            "kk_serials": "kk_serials",
            "i2c_control": "i2c_control",
            "collection": "mcu_io",
        }
        # PMU 工具子项：先选定子项再点击父按钮
        _pmu_tool_subkeys = {
            "pmu_1811": "1811",
            "pmu_1860": "1860",
        }
        # VminHunter 子项：先选定子项再点击父按钮
        _vmin_hunter_subkeys = {
            "vmin_hunter": "hunt",
            "vmin_single_test": "single_test",
        }
        # N6705C Suite 子页：点击父按钮后切到目标 tab
        _suite_subkeys = {
            "power_analyser": "analyser",
            "datalog": "datalog",
        }
        if page in _collection_subkeys:
            self.nav.current_collection_key = _collection_subkeys[page]
        if page in _pmu_tool_subkeys:
            self.nav.current_pmu_tool_key = _pmu_tool_subkeys[page]
        if page in _vmin_hunter_subkeys:
            self.nav.current_vmin_hunter_key = _vmin_hunter_subkeys[page]
        button = button_map.get(page)
        if button is None:
            return False, f"未知页面：{page}"
        self.nav.handle_nav_button_clicked(button)
        if page in _suite_subkeys and self.n6705c_suite_ui is not None:
            self.n6705c_suite_ui.switch_page(_suite_subkeys[page])
        return True, f"已跳转到 {page}"

    def _ai_toggle_panel(self, want_open):
        button = getattr(self.top_bar, "ai_panel_button", None)
        if button is None:
            return False, "面板按钮不可用。"
        button.setChecked(bool(want_open))
        return True, "面板已打开。" if want_open else "面板已关闭。"

    def _ai_serial_send_text(self, text, newline):
        manager = self._current_serial_manager()
        if manager is None:
            return False, "当前无串口管理器。"
        session = manager.active_session
        if session is None or not getattr(session, "connected", False):
            return False, "当前无已连接的活动串口会话。"
        try:
            ok = manager.send_to_active_session((text + newline).encode("utf-8"))
        except Exception:  # noqa: BLE001 - 发送异常转可读结果
            logger.error("AI 串口发送失败", exc_info=True)
            return False, "串口发送异常，请查看日志。"
        return bool(ok), "已发送。" if ok else "发送失败。"

    def _ai_serial_clear(self):
        service = getattr(self, "ai_service", None)
        if service is not None:
            service.rx_cache.clear()
        return True, "已清空 AI 侧串口接收缓存。"

    def _ai_serial_list_ports(self):
        """枚举系统可用串口（供 AI list_serial_ports 动作调用）。

        经 core.serial_io.serial_backend 本地枚举，返回设备名/描述/硬件 ID。
        """
        try:
            from core.serial_io.serial_backend import list_serial_ports

            return [
                {
                    "device": p.device,
                    "description": p.description or "",
                    "hwid": p.hwid or "",
                }
                for p in list_serial_ports()
            ]
        except Exception:  # noqa: BLE001 - 枚举失败回空列表，不致命
            logger.error("AI 枚举串口失败", exc_info=True)
            return []

    def _ai_test_run(self):
        page = self.resolve_active_ai_page()
        if page is None or CAP_START_TEST not in _ai_caps(page):
            return False, "当前页面不支持由 AI 启动测试。"
        try:
            ok, message = page.ai_start_test()
        except Exception:  # noqa: BLE001 - 启动异常转可读结果
            logger.error("AI 启动测试失败", exc_info=True)
            return False, "启动测试异常，请查看日志。"
        if not ok:
            return False, message or "启动失败。"
        # 注意：pending 任务由 start_test_sequence handler 统一登记（kind="test_sequence"
        # 并把 task_id 回给 AI）。此处不再重复登记，否则会产生 kind 不一致的孤儿任务，
        # 导致序列完成后无法回灌、TaskTray「进行中」清不掉、AI 一直卡住（§4 / S3-2）。
        #
        # 完成回灌依赖页面的 sequence_execution_finished 信号（Orchestrator 在创建时
        # 已连接；PMU/Charger 等专项子页在此按需幂等连接，避免漏接导致 task 永远 pending）。
        sig = getattr(page, "sequence_execution_finished", None)
        if sig is not None:
            try:
                sig.connect(
                    self._ai_on_sequence_finished_resume, Qt.UniqueConnection
                )
            except (RuntimeError, TypeError):
                # 已连接（UniqueConnection 重复）即跳过，不影响后续回灌
                pass
        return True, message or "已请求启动测试。"

    def _ai_on_sequence_finished_resume(self, success: bool, message: str):
        """测试序列完成 → 回灌对应 pending 任务并触发续跑（§4 / S3-2）。"""
        registry = self.ai_service.pending_task_registry
        session_key = self.ai_service.current_session_key()
        target = None
        for t in registry.list(session_key=session_key):
            if (
                t.get("kind") == "test_sequence"
                and t.get("status") == "pending"
                and not t.get("resumed")
            ):
                target = t
        if target is None:
            return
        result = {
            "ok": bool(success),
            "verdict": "PASS" if success else "FAIL",
            "detail": message,
            "_message": f"测试序列执行完成：{'PASS' if success else 'FAIL'}。{message}",
        }
        self.ai_service.resume_with_task_result(
            target.get("task_id"), result, kind="test_sequence", title="测试序列"
        )

    def _ai_test_pause(self):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return False, "请先切换到 Orchestrator 页面。"
        try:
            ui._on_pause()
        except Exception:  # noqa: BLE001 - 暂停异常转可读结果
            logger.error("AI 暂停测试序列失败", exc_info=True)
            return False, "暂停测试序列异常，请查看日志。"
        return True, "已切换暂停/恢复。"

    def _ai_test_stop(self):
        page = self.resolve_active_ai_page()
        if page is None or CAP_STOP_TEST not in _ai_caps(page):
            return False, "当前页面不支持由 AI 停止测试。"
        try:
            ok, message = page.ai_stop_test()
        except Exception:  # noqa: BLE001 - 停止异常转可读结果
            logger.error("AI 停止测试失败", exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return bool(ok), message or ("已发送停止请求。" if ok else "停止失败。")

    def _ai_chamber_wait_stable(self, session_id, target, tolerance, timeout):
        """温箱等待稳定：经 worker 线程运行 TemperatureStabilizer，QEventLoop 保持 UI 响应。

        执行期持 busy 租约，避免其它流程改温度；判稳跑在独立线程，主线程经
        QEventLoop + QTimer 轮询 future 完成状态，不阻塞 UI 事件循环。返回结果 dict
        供 chamber_wait_stable handler 回灌模型。
        """
        from concurrent.futures import ThreadPoolExecutor

        from instruments.chambers import TemperatureStabilizer

        manager = self.instrument_manager
        session = manager.get_session(session_id)
        if session is None or not session.connected:
            return {"ok": False, "_message": f"会话未连接：{session_id}"}
        chamber = manager.get_instance(session_id)
        if chamber is None:
            return {"ok": False, "_message": f"无法获取温箱实例：{session_id}"}
        if not manager.try_set_busy(session_id, True, owner="AIAssist"):
            owner = getattr(session, "busy_owner", "")
            return {
                "ok": False,
                "_message": f"温箱忙（owner={owner or '未知'}），拒绝等待以免冲突。",
            }

        stabilizer = TemperatureStabilizer(
            chamber,
            poll_interval=5.0,
            window_seconds=60.0,
            tolerance=tolerance,
            stable_hits=2,
            max_wait_s=timeout,
            arrive_tolerance=1.0,
            log_fn=lambda msg: logger.info("chamber_wait_stable[%s]: %s", session_id, msg),
            stop_check=None,
        )

        box: dict = {}

        def _run():
            try:
                box["result"] = stabilizer.wait_for_stable(target)
            except Exception as exc:  # noqa: BLE001 - 透传给主线程统一处理
                box["error"] = exc

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_run)

        loop = QEventLoop()

        def _on_poll():
            if future.done():
                poll.stop()
                loop.quit()

        poll = QTimer()
        poll.setInterval(100)
        poll.timeout.connect(_on_poll)
        poll.start()
        if not future.done():
            loop.exec()
        poll.stop()
        executor.shutdown(wait=False)

        try:
            manager.try_set_busy(session_id, False, owner="AIAssist")
        except Exception:  # noqa: BLE001 - 释放租约失败不掩盖主结果
            logger.error("释放温箱租约失败：%s", session_id, exc_info=True)

        if "error" in box:
            return {"ok": False, "_message": f"等待稳定异常：{box['error']}"}
        result = box.get("result")
        if result is None:
            return {"ok": False, "_message": "等待稳定未返回结果。"}

        actual = result.actual
        actual_txt = f"{actual:.2f}" if isinstance(actual, (int, float)) else str(actual)
        if result.stable:
            msg = f"温度已稳定：{actual_txt} °C（耗时 {result.waited_s:.0f}s）。"
        else:
            msg = (
                f"未稳定（{result.reason}）：当前 {actual_txt} °C，"
                f"已等待 {result.waited_s:.0f}s。"
            )
        return {
            "ok": bool(result.stable),
            "session_id": session_id,
            "stable": bool(result.stable),
            "reason": result.reason,
            "target": result.target,
            "actual": actual,
            "waited_s": round(result.waited_s, 1),
            "poll_count": result.poll_count,
            "_message": msg,
        }

    def _get_ai_page_key(self):
        return self._get_current_help_key()

    def _update_ai_apply_callbacks(self):
        panel = getattr(self, "ai_panel", None)
        if panel is None:
            return
        if self.current_instrument_ui == "orchestrator":
            panel.set_script_apply_callback(self._apply_ai_script_draft)
        else:
            panel.set_script_apply_callback(None)
        panel.set_config_apply_callback(self._apply_ai_config_draft)

        service = getattr(self, "ai_service", None)
        if service is not None:
            if self.current_instrument_ui == "orchestrator":
                service.set_sequence_data_getter(self._get_ai_sequence_data)
            else:
                service.set_sequence_data_getter(None)

        if self.current_instrument_ui == "datalog":
            panel.set_waveform_provider_callback(self._provide_ai_waveform_digest)
            panel.set_waveform_range_getter(self._provide_ai_waveform_range)
            panel.set_waveform_marker_getter(self._provide_ai_waveform_marker)
        else:
            panel.set_waveform_provider_callback(None)
            panel.set_waveform_range_getter(None)
            panel.set_waveform_marker_getter(None)

    def _get_ai_sequence_data(self):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or self.current_instrument_ui != "orchestrator":
            return None
        return ui.get_ai_sequence_data()

    def _provide_ai_waveform_digest(self, x_range=None, marker=None):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.build_waveform_digest(x_range=x_range, marker=marker)

    def _provide_ai_waveform_range(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.get_visible_x_range()

    def _provide_ai_waveform_marker(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.get_marker_window()

    def _provide_ai_waveform_windowed(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return None
        return ui.get_waveform_data_windowed()

    def _provide_ai_waveform_full(self):
        """返回 Datalog 页全量波形数据（未按可见窗口裁剪），供 P6 波形 CSV 导出切片。"""
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return None
        getter = getattr(ui, "get_waveform_data", None)
        if not callable(getter):
            return None
        return getter()

    def _ai_export_datalog_csv(self, session_id, dir_path):
        """P6 Datalog CSV 导出回调：委托 Datalog 页非交互式导出到指定目录。

        session_id 仅用于审计追溯；实际导出的是当前 Datalog 页内存中的可见通道数据。
        返回 {ok, path, rows, channels, bytes, message} 供 export_datalog_csv handler 回灌。
        """
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return {"ok": False, "message": "当前不在 Datalog 页面，无法导出。"}
        exporter = getattr(ui, "export_combined_csv_to_path", None)
        if not callable(exporter):
            return {"ok": False, "message": "Datalog 页面不支持非交互式导出。"}
        try:
            return exporter(dir_path)
        except Exception:  # noqa: BLE001 - 导出异常转可读结果
            logger.error("AI Datalog CSV 导出失败", exc_info=True)
            return {"ok": False, "message": "导出异常，请查看日志。"}

    def _apply_ai_script_draft(self, nodes):
        ui = getattr(self, "orchestrator_ui", None)
        if ui is None or getattr(ui, "canvas", None) is None:
            return False, "Orchestrator 页面不可用。"
        if getattr(ui.canvas, "_running", False):
            return False, "序列运行中，无法应用草案。"
        try:
            ui.canvas.load_from_nodes(nodes)
        except Exception:
            logger.error("应用 AI 脚本草案到画布失败", exc_info=True)
            return False, "应用到画布失败，请查看日志。"
        return True, ""

    def _apply_ai_config_draft(self, draft):
        page = self.resolve_active_ai_page()
        if page is None or CAP_APPLY_CONFIG not in _ai_caps(page):
            return False, "当前页面不支持应用配置草案。"
        importer = getattr(page, "ai_apply_config", None)
        if not callable(importer):
            return False, "当前页面尚未实现配置草案导入接口。"
        try:
            ok, message = importer(draft.payload)
        except Exception:
            logger.error("应用 AI 配置草案失败", exc_info=True)
            return False, "应用配置失败，请查看日志。"
        if ok is False:
            return False, message or "页面拒绝了该配置草案。"
        return True, message or ""

    def _ai_ui_invoke(self, action_id: str) -> tuple[bool, str]:
        """§5b 枢纽：按当前页 page_key 路由 ui_invoke 到已登记的按钮原槽。

        链路：查 UIActionRegistry（page_key 匹配 + enabled_when）→ 不满足明示不可用
        → 主线程调 spec.handler()（按钮原槽，行为与人点一致）→ [AI] 日志回填主区。
        page_key 隔离：仅能触发 page_key == 当前页 的动作，禁跨页派发。
        """
        registry = getattr(self, "_ui_action_registry", None)
        if registry is None:
            return False, "UI 动作注册表未启用。"
        page_key = self._get_ai_page_key()
        if not page_key:
            return False, "无法确定当前页面。"
        spec = registry.get(page_key, action_id)
        if spec is None:
            return False, f"未登记或非当前页的 UI 动作：{action_id}"
        if not spec.is_enabled():
            return False, f"「{spec.label}」当前不可用（不满足触发前置条件）。"
        try:
            ok, message = spec.handler()
        except Exception:
            logger.error("ui_invoke 执行失败: %s", action_id, exc_info=True)
            return False, f"「{spec.label}」执行异常，详见日志。"
        ok = bool(ok)
        # §5b.6：[AI] 日志回填主区（页面有 append_log 即追加，AI 面板由 action_result 显示）
        log_msg = f"[AI] 触发 {spec.label}：{message or ('成功' if ok else '失败')}"
        page = self._current_active_page()
        appender = getattr(page, "append_log", None) if page is not None else None
        if callable(appender):
            try:
                appender(log_msg)
            except Exception:  # noqa: BLE001
                logger.error("ui_invoke 追加 [AI] 日志失败", exc_info=True)
        if ok:
            return True, message or f"已触发「{spec.label}」。"
        return False, message or f"「{spec.label}」触发失败。"

    def _wire_serial_rx_to_ai(self, page):
        manager = getattr(page, "_sc_session_manager", None)
        if manager is None or getattr(self, "ai_service", None) is None:
            return
        manager.session_data_received.connect(self.ai_service.feed_serial_rx)

    def _current_serial_manager(self):
        page = getattr(self, "kk_serials_ui", None)
        if page is None:
            return None
        return getattr(page, "_sc_session_manager", None)

    def _get_ai_serial_status(self):
        manager = self._current_serial_manager()
        if manager is None:
            return None
        session = manager.active_session
        if session is None:
            return None
        return {
            "session_id": session.session_id,
            "port": getattr(session, "port", "") or "",
            "baudrate": getattr(session, "baudrate", 0),
            "connected": bool(getattr(session, "connected", False)),
            "rx_bytes": getattr(session, "rx_bytes", 0),
            "tx_bytes": getattr(session, "tx_bytes", 0),
        }

    def _get_ai_execution_logs(self):
        page = self._current_active_page()
        logs_frame = getattr(page, "logs_frame", None) if page is not None else None
        if logs_frame is None:
            return []
        raw_logs = getattr(logs_frame, "_all_logs", [])
        return [str(raw) for raw, _html in raw_logs]

    def resolve_active_ai_page(self):
        """返回当前可被 AI 控制的页面对象（含 Tab 子页下钻），无则 None。

        - Orchestrator：返回 orchestrator_ui（契约实现者之一）；
        - Tab 容器页（pmu_test / charger_test / vmin_hunter）：下钻到 tab_widget.currentWidget()，
          使 AI 能力裁剪与子页 page_key 对齐（如 pmu_dcdc_efficiency）；
        - 其它页：返回页面实例本身（若实现契约方法即可被 AI 控制）。
        """
        page_key = self.current_instrument_ui
        if page_key == "orchestrator":
            return getattr(self, "orchestrator_ui", None)
        # Tab 容器页：下钻到当前子页
        if page_key in ("pmu_test", "charger_test", "module_test", "consumption_test",
                        "vmin_hunter"):
            attr = f"{page_key}_ui"
            container = getattr(self, attr, None)
            if container is None:
                return None
            tab_widget = getattr(container, "tab_widget", None)
            if tab_widget is not None:
                return tab_widget.currentWidget()
            return container
        # 其它页：返回页面实例本身
        return None
