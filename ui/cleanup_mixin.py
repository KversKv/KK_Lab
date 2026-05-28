from log_config import get_logger

logger = get_logger(__name__)


class CleanupMixin:
    def _cleanup_sub_ui(self, sub_ui, name):
        try:
            if hasattr(sub_ui, 'cleanup_threads') and callable(sub_ui.cleanup_threads):
                logger.info("[CloseEvent] Cleaning up threads: %s", name)
                sub_ui.cleanup_threads()
        except Exception as e:
            logger.warning("[CloseEvent] Error cleaning up threads for %s: %s", name, e)

        try:
            if hasattr(sub_ui, 'test_worker') and sub_ui.test_worker is not None:
                logger.info("[CloseEvent] Stopping test worker: %s", name)
                if hasattr(sub_ui.test_worker, 'request_stop'):
                    sub_ui.test_worker.request_stop()
                elif hasattr(sub_ui.test_worker, 'stop'):
                    sub_ui.test_worker.stop()
            if hasattr(sub_ui, '_test_worker') and sub_ui._test_worker is not None:
                logger.info("[CloseEvent] Stopping test worker: %s", name)
                if hasattr(sub_ui._test_worker, 'request_stop'):
                    sub_ui._test_worker.request_stop()
                elif hasattr(sub_ui._test_worker, 'stop'):
                    sub_ui._test_worker.stop()
            if hasattr(sub_ui, 'test_thread') and sub_ui.test_thread is not None:
                logger.info("[CloseEvent] Waiting for test thread to finish: %s", name)
                sub_ui.test_thread.quit()
                sub_ui.test_thread.wait(3000)
                sub_ui.test_thread = None
        except Exception as e:
            logger.warning("[CloseEvent] Error stopping test thread for %s: %s", name, e)

        try:
            if hasattr(sub_ui, 'rm') and sub_ui.rm is not None:
                logger.info("[CloseEvent] Closing VISA ResourceManager: %s", name)
                sub_ui.rm.close()
                sub_ui.rm = None
        except Exception as e:
            logger.warning("[CloseEvent] Error closing ResourceManager for %s: %s", name, e)

        try:
            if hasattr(sub_ui, 'close_serial') and callable(sub_ui.close_serial):
                if getattr(sub_ui, '_serial_conn', None) is not None \
                        or getattr(sub_ui, '_serial_connected', False):
                    logger.info("[CloseEvent] Closing serial connection: %s", name)
                    sub_ui.close_serial()
        except Exception as e:
            logger.warning("[CloseEvent] Error closing serial connection for %s: %s", name, e)

    def _perform_close_cleanup(self):
        logger.info("[CloseEvent] Window close requested, cleaning up resources...")

        if self.visa_instrument:
            logger.info("[CloseEvent] Disconnecting VISA instrument...")
            try:
                self.visa_instrument.disconnect()
            except Exception as e:
                logger.warning("[CloseEvent] Error disconnecting VISA instrument: %s", e)

        if getattr(self, "chamber", None):
            logger.info("[CloseEvent] Closing chamber (legacy)...")
            try:
                self.chamber.close()
            except Exception as e:
                logger.warning("[CloseEvent] Error closing chamber: %s", e)
            self.chamber = None

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
                logger.info("[CloseEvent] Closing VISA ResourceManager: %s", ui_name)
                try:
                    ui_widget.rm.close()
                except Exception as e:
                    logger.warning("[CloseEvent] Error closing ResourceManager for %s: %s", ui_name, e)
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
                logger.warning("[CloseEvent] Error closing KK Serials: %s", e)

        logger.info("[CloseEvent] All resources cleaned up, closing window.")
