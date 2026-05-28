__all__ = [
    "TestManager",
    "DataCollector",
    "InstrumentManager",
]


def __getattr__(name):
    if name == "TestManager":
        from core.test_manager import TestManager
        return TestManager
    if name == "DataCollector":
        from core.data_collector import DataCollector
        return DataCollector
    if name == "InstrumentManager":
        from core.instruments import InstrumentManager
        return InstrumentManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
