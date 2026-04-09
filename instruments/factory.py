from instruments.scopes.keysight.dsox4034a import DSOX4034A
from instruments.scopes.tektronix.mso64b import MSO64B
from instruments.power.keysight.n6705c import N6705C
from instruments.chambers.vt6002_chamber import VT6002
from instruments.base.visa_instrument import VisaInstrument


def create_oscilloscope(osc_type: str, resource: str):
    if osc_type == "dsox4034a":
        return DSOX4034A(resource)
    elif osc_type == "mso64b":
        return MSO64B(resource)
    else:
        raise ValueError(f"Unknown oscilloscope type: {osc_type}")


def create_power_analyzer(resource: str):
    return N6705C(resource)


def create_chamber(port: str, baudrate: int = 9600):
    return VT6002(port, baudrate)
