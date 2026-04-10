import pyvisa
import struct
import sys
import logging

logger = logging.getLogger(__name__)


#USB0::0x0957::0x17A4::MY61500152::INSTR

# Global variables
input_channel = "CHANnel2"
setup_file_name = "setup.scp"
screen_image_file_name = "screen_image.png"
waveform_data_file_name = "waveform_data.csv"
wfm_fmt = "WORD"
debug = False

# Initialize the oscilloscope
def initialize():
    idn_string = do_query_string("*IDN?")
    logger.info("Identification string: '%s'", idn_string)
    do_command("*CLS")
    do_command("*RST")

def capture():
    logger.info("Autoscale.")
    do_command(":AUToscale")
    do_command(":TRIGger:MODE EDGE")
    qresult = do_query_string(":TRIGger:MODE?")
    logger.info("Trigger mode: %s", qresult)
    do_command(f":TRIGger:EDGE:SOURce {input_channel}")
    qresult = do_query_string(":TRIGger:EDGE:SOURce?")
    logger.info("Trigger edge source: %s", qresult)
    do_command(":TRIGger:EDGE:LEVel 1.5")
    qresult = do_query_string(":TRIGger:EDGE:LEVel?")
    logger.info("Trigger edge level: %s", qresult)
    do_command(":TRIGger:EDGE:SLOPe POSitive")
    qresult = do_query_string(":TRIGger:EDGE:SLOPe?")
    logger.info("Trigger edge slope: %s", qresult)

    setup_bytes = do_query_ieee_block(":SYSTem:SETup?")
    with open(setup_file_name, "wb") as f:
        f.write(setup_bytes)
    logger.info("Setup bytes saved: %d", len(setup_bytes))

def do_query_ieee_block(query):
    if debug:
        logger.debug("Qyb = '%s'", query)
    result = InfiniiVision.query_binary_values(f"{query}", datatype='s', container=bytes)
    check_instrument_errors(query)
    return result

# Analyze data from the oscilloscope
def analyze():
    do_command(f":MEASure:SOURce {input_channel}")
    qresult = do_query_string(":MEASure:SOURce?")
    logger.info("Measure source: %s", qresult)
    do_command(":MEASure:FREQuency")
    qresult = do_query_string(":MEASure:FREQuency?")
    logger.info("Measured frequency on %s: %s", input_channel, qresult)
    do_command(":MEASure:VAMPlitude")
    qresult = do_query_string(":MEASure:VAMPlitude?")
    logger.info("Measured vertical amplitude on %s: %s", input_channel, qresult)

    screen_bytes = do_query_ieee_block(":DISPlay:DATA? PNG, COLor")
    logger.debug("Screen bytes: %d", len(screen_bytes))
    with open(screen_image_file_name, "wb") as f:
        f.write(screen_bytes)
    logger.info("Screen image written to %s.", screen_image_file_name)

# Send a command to the oscilloscope
def do_command(command, hide_params=False):
    if debug:
        logger.debug("Cmd = '%s'", command)
    InfiniiVision.write(f"{command}")
    check_instrument_errors(command)

# Query a string value from the oscilloscope
def do_query_string(query):
    if debug:
        logger.debug("Qys = '%s'", query)
    result = InfiniiVision.query(f"{query}")
    check_instrument_errors(query)
    return result.strip()

# Query a numeric value from the oscilloscope
def do_query_number(query):
    if debug:
        logger.debug("Qyn = '%s'", query)
    results = InfiniiVision.query(f"{query}")
    check_instrument_errors(query)
    return float(results)

# Check for errors after sending a command to the oscilloscope
def check_instrument_errors(command):
    while True:
        error_string = InfiniiVision.query(":SYSTem:ERRor?")
        if error_string.find("+0,", 0, 3) == -1:
            logger.error("ERROR: %s, command: '%s'", error_string, command)
            sys.exit(1)
        else:
            break

# Main function to run the program
def main():
    rm = pyvisa.ResourceManager()
    global InfiniiVision
    InfiniiVision = rm.open_resource("USB0::0x0957::0x17A4::MY61500152::INSTR")
    InfiniiVision.timeout = 15000
    InfiniiVision.clear()

    #initialize()
    #capture()
    analyze()

    InfiniiVision.close()
    logger.info("End of program.")

if __name__ == "__main__":
    main()
