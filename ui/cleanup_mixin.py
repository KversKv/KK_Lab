from log_config import get_logger

logger = get_logger(__name__)


class CleanupMixin:
    def _cleanup_sub_ui(self, sub_ui, name):
        try:
            if hasattr(sub_ui, 'cleanup_threads') and callable(sub_ui.cleanup_threads):
                logger.info(f"[CloseEvent] Cleaning up threads: {name}")
                sub_ui.cleanup_threads()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error cleaning up threads for {name}: {e}")

        try:
            if hasattr(sub_ui, 'test_worker') and sub_ui.test_worker is not None:
                logger.info(f"[CloseEvent] Stopping test worker: {name}")
                if hasattr(sub_ui.test_worker, 'request_stop'):
                    sub_ui.test_worker.request_stop()
                elif hasattr(sub_ui.test_worker, 'stop'):
                    sub_ui.test_worker.stop()
            if hasattr(sub_ui, '_test_worker') and sub_ui._test_worker is not None:
                logger.info(f"[CloseEvent] Stopping test worker: {name}")
                if hasattr(sub_ui._test_worker, 'request_stop'):
                    sub_ui._test_worker.request_stop()
                elif hasattr(sub_ui._test_worker, 'stop'):
                    sub_ui._test_worker.stop()
            if hasattr(sub_ui, 'test_thread') and sub_ui.test_thread is not None:
                logger.info(f"[CloseEvent] Waiting for test thread to finish: {name}")
                sub_ui.test_thread.quit()
                sub_ui.test_thread.wait(3000)
                sub_ui.test_thread = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error stopping test thread for {name}: {e}")

        try:
            if hasattr(sub_ui, 'n6705c') and sub_ui.n6705c is not None:
                logger.info(f"[CloseEvent] Disconnecting N6705C instrument: {name}")
                if hasattr(sub_ui.n6705c, 'instr') and sub_ui.n6705c.instr:
                    sub_ui.n6705c.instr.close()
                sub_ui.n6705c = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error disconnecting N6705C for {name}: {e}")

        try:
            if hasattr(sub_ui, 'Osc_ins') and sub_ui.Osc_ins is not None:
                logger.info(f"[CloseEvent] Disconnecting oscilloscope instrument: {name}")
                osc = sub_ui.Osc_ins
                sub_ui.Osc_ins = None
                sub_ui.scope_connected = False
                if hasattr(osc, 'disconnect'):
                    osc.disconnect()
                elif hasattr(osc, 'instrument') and osc.instrument:
                    osc.instrument.close()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error disconnecting oscilloscope for {name}: {e}")

        try:
            if hasattr(sub_ui, 'rm') and sub_ui.rm is not None:
                logger.info(f"[CloseEvent] Closing VISA ResourceManager: {name}")
                sub_ui.rm.close()
                sub_ui.rm = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error closing ResourceManager for {name}: {e}")

        try:
            if hasattr(sub_ui, 'close_serial') and callable(sub_ui.close_serial):
                if getattr(sub_ui, '_serial_conn', None) is not None \
                        or getattr(sub_ui, '_serial_connected', False):
                    logger.info(f"[CloseEvent] Closing serial connection: {name}")
                    sub_ui.close_serial()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error closing serial connection for {name}: {e}")

    def _perform_close_cleanup(self):
        logger.info("[CloseEvent] Window close requested, disconnecting all instruments...")

        if self.n6705c_top:
            logger.info("[CloseEvent] Disconnecting N6705C Top (all channels)...")
            try:
                self.n6705c_top.disconnect_all()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting N6705C Top: {e}")

        if self.mso64b_top and self.mso64b_top.is_connected:
            scope_type = getattr(self.mso64b_top, 'scope_type', 'MSO64B') or 'oscilloscope'
            logger.info(f"[CloseEvent] Disconnecting {scope_type} oscilloscope...")
            try:
                self.mso64b_top.disconnect()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting {scope_type}: {e}")

        if self.oscilloscope_ui and self.oscilloscope_ui.controller.is_connected:
            logger.info("[CloseEvent] Disconnecting oscilloscope controller...")
            try:
                self.oscilloscope_ui.controller.disconnect_instrument()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting oscilloscope controller: {e}")

        if self.visa_instrument:
            logger.info("[CloseEvent] Disconnecting VISA instrument...")
            try:
                self.visa_instrument.disconnect()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting VISA instrument: {e}")

        if self.vt6002_chamber:
            logger.info("[CloseEvent] Closing VT6002 chamber...")
            try:
                self.vt6002_chamber.close()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing VT6002 chamber: {e}")
            self.vt6002_chamber = None

        if self.vt6002_chamber_ui is not None:
            try:
                if self.vt6002_chamber_ui.vt6002 is not None:
                    logger.info("[CloseEvent] Closing VT6002 chamber UI instrument...")
                    self.vt6002_chamber_ui.vt6002.close()
                    self.vt6002_chamber_ui.vt6002 = None
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing VT6002 chamber UI: {e}")

        if self.consumption_test_ui is not None:
            self._cleanup_sub_ui(self.consumption_test_ui, "ConsumptionTestWrapper")
            if hasattr(self.consumption_test_ui, 'auto_test_ui'):
                self._cleanup_sub_ui(self.consumption_test_ui.auto_test_ui, "ConsumptionTestUI")
            if hasattr(self.consumption_test_ui, 'high_low_temp_ui'):
                self._cleanup_sub_ui(self.consumption_test_ui.high_low_temp_ui, "HighLowTempConsumptionTestUI")

        for ui_name, ui_widget in [
            ("N6705CAnalyserUI", self.n6705c_analyser_ui),
            ("N6705CDatalogUI", self.n6705c_datalog_ui),
        ]:
            if ui_widget is not None and hasattr(ui_widget, 'rm') and ui_widget.rm is not None:
                logger.info(f"[CloseEvent] Closing VISA ResourceManager: {ui_name}")
                try:
                    ui_widget.rm.close()
                except Exception as e:
                    logger.warning(f"[CloseEvent] Error closing ResourceManager for {ui_name}: {e}")
                ui_widget.rm = None

        if self.pmu_test_ui is not None:
            for attr in [
                'dcdc_efficiency_ui', 'output_voltage_ui',
                'is_gain_ui', 'oscp_ui', 'gpadc_test_ui', 'clk_test_ui',
            ]:
                sub_ui = getattr(self.pmu_test_ui, attr, None)
                if sub_ui is not None:
                    self._cleanup_sub_ui(sub_ui, f"PMU.{attr}")

        if self.charger_test_ui is not None:
            for attr in [
                'config_traverse_ui', 'status_register_ui',
                'iterm_ui', 'regulation_voltage_ui',
            ]:
                sub_ui = getattr(self.charger_test_ui, attr, None)
                if sub_ui is not None:
                    self._cleanup_sub_ui(sub_ui, f"Charger.{attr}")

        if self.custom_test_ui is not None:
            self._cleanup_sub_ui(self.custom_test_ui, "CustomTestUI")

        if self.kk_serials_ui is not None:
            try:
                self.kk_serials_ui.close_serial()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing KK Serials: {e}")

        logger.info("[CloseEvent] All instruments disconnected, closing window.")
