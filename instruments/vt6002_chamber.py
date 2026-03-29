import time
import serial
import struct


def crc16(data: bytes):
    """计算Modbus的CRC校验码"""
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def hex_to_int(hex_num, bit_length=16):
    # 计算符号位的位置
    sign_bit = 1 << (bit_length - 1)
    # 如果符号位为1，表示负数
    if (hex_num & sign_bit) >> 15:
        # 计算负数的补码表示
        return hex_num - (1 << bit_length)
    else:
        # 正数直接返回
        return hex_num


class VT6002:
    def __init__(self, port, baudrate=9600):
        """初始化串口连接"""
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.parameters = {
            "温度PV值": "0218",
            "温度设定值": "074E",
            "湿度PV值": "02E0",
            "温度SV值": "0010",
            "湿度SV值": "002E",
            "辅助设定PV": "027C",
            "辅助设定SV": "0086",
            "温度输出": "01D2",
            "湿度输出": "01DC",
            "通讯协议": "00E6",
            "通讯格式": "00E8",
            "地址站号": "00EA",
            "超时时间": "00EC"
        }

    def build_request(self, address_hex):
        """构建Modbus请求帧"""
        address_bytes = bytes.fromhex(address_hex)
        request = bytes([0x01, 0x03]) + address_bytes + bytes([0x00, 0x01])
        crc = crc16(request)
        return request + struct.pack('<H', crc)

    def build_command(self, command):
        crc = crc16(command)
        return command + struct.pack('<H', crc)

    def build_request_write(self, address_hex, value):
        """构建Modbus请求帧"""
        request = bytes([0x01, 0x06]) + bytes(address_hex) + bytes([(value >> 8) & 0xFF, value & 0xFF])
        crc = crc16(request)
        return request + struct.pack('<H', crc)

    def build_request_set_temp(self, temp_celsius):
        # Convert temperature to correct format (e.g., 2.5°C to 0x0019)
        temp_value = int(temp_celsius * 10)
        request = bytes([0x01, 0x06, 0x07, 0x4E, (temp_value >> 8) & 0xFF, temp_value & 0xFF])
        crc = crc16(request)
        return request + struct.pack('<H', crc)

    def read_value(self, address_hex):
        """读取指定地址的数据"""
        self.ser.write(self.build_request(address_hex))
        response = self.ser.read(7)
        if len(response) == 7:
            temp_bytes = response[3:5]  # 假设温度值在字节3-4（FF E8）
            value = int.from_bytes(temp_bytes, byteorder="big", signed=True)
            if address_hex == '0218':
                return value / 10
            else:
                return value
        else:
            print(f"错误: 地址 {address_hex} 响应不完整")
            return None

    def write_value(self, address_hex, value_to_be_write):
        """读取指定地址的数据"""

        self.ser.write(self.build_request(address_hex))
        response = self.ser.read(7)
        if len(response) == 7:
            value_high, value_low = response[3], response[4]
            value = (value_high << 8) | value_low
            if (address_hex == '0218'):
                return value / 10
            else:
                return value
        else:
            print(f"错误: 地址 {address_hex} 响应不完整")
            return None

    def set_temperature(self, temp_celsius):
        self.ser.write(self.build_request_set_temp(temp_celsius))
        # print(self.build_request_set_temp(temp_celsius))
        response = self.ser.read(8)
        # if response == self.build_request_set_temp(temp_celsius):
        #     print(f"Temperature set to {temp_celsius}°C successfully.")
        # else:
        #     print("Error: Failed to set temperature.")

    def set_temperature2(self, temp_celsius):
        values = self.build_request_write([0x07, 0x4E], temp_celsius)
        self.ser.write(values)
        response = self.ser.read(8)
        if response == values:
            print(f"Temperature set to {temp_celsius}°C successfully.")
        else:
            print("Error: Failed to set temperature.")

    def get_current_temp(self):
        """读取温度PV值"""
        return self.read_value(self.parameters["温度PV值"])

    def get_set_temp(self):
        """读取温度PV值"""
        value = self.read_value(self.parameters["温度设定值"])
        value2 = hex_to_int(value)
        return value2 / 10

    def read_humidity_pv(self):
        """读取湿度PV值"""
        return self.read_value(self.parameters["湿度PV值"])

    def read_temperature_sv(self):
        """读取温度SV值"""
        return self.read_value(self.parameters["温度SV值"])

    def read_humidity_sv(self):
        """读取湿度SV值"""
        return self.read_value(self.parameters["湿度SV值"])

    def read_aux_pv(self):
        """读取辅助设定PV"""
        return self.read_value(self.parameters["辅助设定PV"])

    def read_aux_sv(self):
        """读取辅助设定SV"""
        return self.read_value(self.parameters["辅助设定SV"])

    def read_temperature_output(self):
        """读取温度输出"""
        return self.read_value(self.parameters["温度输出"])

    def read_humidity_output(self):
        """读取湿度输出"""
        return self.read_value(self.parameters["湿度输出"])

    def read_communication_protocol(self):
        """读取通讯协议"""
        return self.read_value(self.parameters["通讯协议"])

    def read_communication_format(self):
        """读取通讯格式"""
        return self.read_value(self.parameters["通讯格式"])

    def read_address(self):
        """读取地址站号"""
        return self.read_value(self.parameters["地址站号"])

    def read_timeout(self):
        """读取超时时间"""
        return self.read_value(self.parameters["超时时间"])

    def start(self):
        start_constant_temp_reg1 = bytes([0x01, 0x05, 0x00, 0xd4, 0xff, 0x00])
        start_constant_temp_reg1 = self.build_command(start_constant_temp_reg1)
        self.ser.write(start_constant_temp_reg1)
        response = self.ser.read(8)
        start_constant_temp_reg2 = bytes([0x01, 0x05, 0x04, 0xb0, 0xff, 0x00])
        start_constant_temp_reg2 = self.build_command(start_constant_temp_reg2)
        self.ser.write(start_constant_temp_reg2)
        response = self.ser.read(8)
        if response == start_constant_temp_reg2:
            print(f"Constant temp start successfully.")
        else:
            print("Error: Failed to set temperature.")

    def stop(self):
        start_constant_temp_reg1 = bytes([0x01, 0x05, 0x00, 0xd5, 0xff, 0x00])
        start_constant_temp_reg1 = self.build_command(start_constant_temp_reg1)
        self.ser.write(start_constant_temp_reg1)
        response = self.ser.read(8)
        start_constant_temp_reg2 = bytes([0x01, 0x05, 0x04, 0xb0, 0x00, 0x00])
        start_constant_temp_reg2 = self.build_command(start_constant_temp_reg2)
        self.ser.write(start_constant_temp_reg2)
        response = self.ser.read(8)
        if response == start_constant_temp_reg2:
            print(f"Constant temp close successfully.")
        else:
            print("Error: Failed to set temperature.")

    def close(self):
        """关闭串口连接"""
        if self.ser.is_open:
            self.ser.close()


# 使用示例
if __name__ == "__main__":
    vt6002 = VT6002("COM9")  # 根据实际串口号修改
    try:
        # print("湿度PV值:", vt6002.read_humidity_pv())
        # print("温度SV值:", vt6002.read_temperature_sv())
        # print("湿度SV值:", vt6002.read_humidity_sv())
        # print("辅助设定PV:", vt6002.read_aux_pv())
        # print("辅助设定SV:", vt6002.read_aux_sv())
        # print("温度输出:", vt6002.read_temperature_output())
        # print("湿度输出:", vt6002.read_humidity_output())
        # print("通讯协议:", vt6002.read_communication_protocol())
        # print("通讯格式:", vt6002.read_communication_format())
        # print("地址站号:", vt6002.read_address())
        # print("超时时间:", vt6002.read_timeout())
        vt6002.set_temperature(25)
        print("温度PV值:", vt6002.get_current_temp())
        print("温度设定值:", vt6002.get_set_temp())
        vt6002.start()
        time.sleep(5)
        vt6002.stop()


    finally:
        vt6002.close()
