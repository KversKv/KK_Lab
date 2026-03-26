import pyvisa


class MSO64B:
    def __init__(self, resource):
        self.rm = pyvisa.ResourceManager('@py')
        if resource.startswith('TCPIP0::') or resource.startswith('USB0::'):
            self.instrument = self.rm.open_resource(resource)
        else:
            self.instrument = self.rm.open_resource(f'TCPIP0::{resource}::inst0::INSTR')
        self.instrument.timeout = 10000
        self.instrument.encoding = 'utf-8'
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'

    def identify_instrument(self):
        return self.instrument.query('*IDN?').strip()

    def get_channel_mean(self, channel):
        self.instrument.write(f'MEASUrement:IMMed:SOURCE1 CH{channel}')
        self.instrument.write('MEASUrement:IMMed:TYPE MEAN')
        return float(self.instrument.query('MEASUrement:IMMed:VALUE?').strip())

    def get_channel_pk2pk(self, channel):
        self.instrument.write(f'MEASUrement:IMMed:SOURCE1 CH{channel}')
        self.instrument.write('MEASUrement:IMMed:TYPE PK2PK')
        return float(self.instrument.query('MEASUrement:IMMed:VALUE?').strip())

    def disconnect(self):
        if self.instrument is not None:
            self.instrument.close()
            self.instrument = None


if __name__ == '__main__':
    ip_address = '192.168.3.27'
    mso64b = MSO64B(ip_address)

    try:
        print(mso64b.identify_instrument())
        print(f'CH2 Mean: {mso64b.get_channel_mean(2):.6f}')
        print(f'CH2 Peak-to-Peak: {mso64b.get_channel_pk2pk(2):.6f}')
    finally:
        mso64b.disconnect()
