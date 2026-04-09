class InstrumentError(Exception):
    pass


class InstrumentConnectionError(InstrumentError):
    pass


class MeasurementError(InstrumentError):
    pass
