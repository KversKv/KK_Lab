from instruments.scopes.keysight.dsox4034a import DSOX4034A
from instruments.scopes.tektronix.mso64b import MSO64B
from instruments.power.keysight.n6705c import N6705C
from instruments.chambers.vt6002_chamber import VT6002
from instruments.base.visa_instrument import VisaInstrument
from log_config import get_logger

logger = get_logger(__name__)


def create_oscilloscope(osc_type: str, resource: str):
    logger.debug("create_oscilloscope: type=%s, resource=%s", osc_type, resource)
    if osc_type == "dsox4034a":
        return DSOX4034A(resource)
    elif osc_type == "mso64b":
        return MSO64B(resource)
    else:
        raise ValueError(f"Unknown oscilloscope type: {osc_type}")


def create_power_analyzer(resource: str):
    logger.debug("create_power_analyzer: resource=%s", resource)
    return N6705C(resource)


def create_chamber(port: str, baudrate: int = 9600):
    logger.debug("create_chamber: port=%s, baudrate=%d", port, baudrate)
    return VT6002(port, baudrate)
