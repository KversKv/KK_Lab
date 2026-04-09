import pyvisa
import struct
import sys


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
    print(f"Identification string: '{idn_string}'")
    do_command("*CLS")
    do_command("*RST")

# Capture data from the oscilloscope
def capture():
    print("Autoscale.")
    do_command(":AUToscale")
    do_command(":TRIGger:MODE EDGE")
    qresult = do_query_string(":TRIGger:MODE?")
    print(f"Trigger mode: {qresult}")
    do_command(f":TRIGger:EDGE:SOURce {input_channel}")
    qresult = do_query_string(":TRIGger:EDGE:SOURce?")
    print(f"Trigger edge source: {qresult}")
    do_command(":TRIGger:EDGE:LEVel 1.5")
    qresult = do_query_string(":TRIGger:EDGE:LEVel?")
    print(f"Trigger edge level: {qresult}")
    do_command(":TRIGger:EDGE:SLOPe POSitive")
    qresult = do_query_string(":TRIGger:EDGE:SLOPe?")
    print(f"Trigger edge slope: {qresult}")

    # Save oscilloscope setup to a file
    setup_bytes = do_query_ieee_block(":SYSTem:SETup?")
    with open(setup_file_name, "wb") as f:
        f.write(setup_bytes)
    print(f"Setup bytes saved: {len(setup_bytes)}")

def do_query_ieee_block(query):
    if debug:
        print(f"Qyb = '{query}'")
    result = InfiniiVision.query_binary_values(f"{query}", datatype='s', container=bytes)
    check_instrument_errors(query)
    return result

# Analyze data from the oscilloscope
def analyze():
    do_command(f":MEASure:SOURce {input_channel}")
    qresult = do_query_string(":MEASure:SOURce?")
    print(f"Measure source: {qresult}")
    do_command(":MEASure:FREQuency")
    qresult = do_query_string(":MEASure:FREQuency?")
    print(f"Measured frequency on {input_channel}: {qresult}")
    do_command(":MEASure:VAMPlitude")
    qresult = do_query_string(":MEASure:VAMPlitude?")
    print(f"Measured vertical amplitude on {input_channel}: {qresult}")

    # Save the screen image to a file
    screen_bytes = do_query_ieee_block(":DISPlay:DATA? PNG, COLor")
    print(screen_bytes)
    with open(screen_image_file_name, "wb") as f:
        f.write(screen_bytes)
    print(f"Screen image written to {screen_image_file_name}.")

# Send a command to the oscilloscope
def do_command(command, hide_params=False):
    if debug:
        print(f"Cmd = '{command}'")
    InfiniiVision.write(f"{command}")
    check_instrument_errors(command)

# Query a string value from the oscilloscope
def do_query_string(query):
    if debug:
        print(f"Qys = '{query}'")
    result = InfiniiVision.query(f"{query}")
    check_instrument_errors(query)
    return result.strip()

# Query a numeric value from the oscilloscope
def do_query_number(query):
    if debug:
        print(f"Qyn = '{query}'")
    results = InfiniiVision.query(f"{query}")
    check_instrument_errors(query)
    return float(results)

# Check for errors after sending a command to the oscilloscope
def check_instrument_errors(command):
    while True:
        error_string = InfiniiVision.query(":SYSTem:ERRor?")
        if error_string.find("+0,", 0, 3) == -1:  # If not "No error".
            print(f"ERROR: {error_string}, command: '{command}'")
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
    print("End of program.")

if __name__ == "__main__":
    main()
