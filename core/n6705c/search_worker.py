# -*- coding: utf-8 -*-
"""
N6705C VISA 搜索 Worker（仅依赖 QtCore，无 QtWidgets）。

从 ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py 平移而来，
行为零变更。
"""

import pyvisa
from PySide6.QtCore import QThread, Signal


class SearchThread(QThread):
    search_result = Signal(str, list)

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._label = label

    def run(self):
        found = []
        rm = None
        try:
            try:
                rm = pyvisa.ResourceManager()
            except Exception:
                rm = pyvisa.ResourceManager('@ni')
            resources = list(rm.list_resources()) or []
            seen = {}
            for res in resources:
                try:
                    instr = rm.open_resource(res, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    if "N6705C" in idn:
                        parts = idn.split(",")
                        serial = parts[2].strip() if len(parts) > 2 else res
                        if serial in seen:
                            if "hislip" in res and "hislip" not in seen[serial]:
                                seen[serial] = res
                        else:
                            seen[serial] = res
                except Exception:
                    pass
            found = list(seen.values())
        except Exception:
            pass
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass
        self.search_result.emit(self._label, found)
