import time
import serial


class MT3065:
    def __init__(self, port="COM10", baudrate=19200):
        """初始化串口连接"""
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def build_command(self, command):
        return (command + "\r").encode()

    def send_command(self, command):
        request = self.build_command(command)
        self.ser.write(request)
        response = self.ser.read(1024)  # 读取返回
        # print("原始响应:", response)  # 调试用，可注释掉
        return response.decode(errors='ignore').strip()

    def get_current_temp(self):
        """读取温度PV值，返回当前温度、设定温度、温度上限、温度下限的元组"""
        command = "1,TEMP?"
        response = self.send_command(command)
        # 解析响应，提取温度数据
        lines = [line.strip() for line in response.split('\r\n') if line.strip()]
        if not lines:
            return (None, None, None, None)
        data_line = lines[0]
        parts = data_line.split(',')
        if len(parts) == 4:
            try:
                current = parts[0]
                setpoint = parts[1]
                upper = parts[2]
                lower = parts[3]
                # 去除可能的额外空格或不可见字符
                print(current.strip())
                return current.strip()

                # return (
                #     current.strip(),
                #     setpoint.strip(),
                #     upper.strip(),
                #     lower.strip()
                # )
            except Exception as e:
                print(f"解析温度数据时出错: {e}")
                return (None, None, None, None)
        else:
            print(f"响应格式不正确: {response}")
            return (None, None, None, None)

    def set_temperature(self, temp_celsius):
        """设置温度设定值"""
        command = f"1,TEMP,S{temp_celsius}"
        response = self.send_command(command)
        if "OK" in response:
            print(f"温度设置为 {temp_celsius}°C 成功。")
        else:
            print("错误: 设置温度失败。")

    def start(self):
        """启动温箱"""
        command = "1,POWER,ON"
        response = self.send_command(command)
        if "OK" in response:
            print("温箱启动成功。")
        else:
            print("错误: 启动失败。")

    def stop(self):
        """停止温箱"""
        command = "1,POWER,OFF"
        response = self.send_command(command)
        if "OK" in response:
            print("温箱停止成功。")
        else:
            print("错误: 停止失败。")

    def close(self):
        if self.ser.is_open:
            self.ser.close()


if __name__ == "__main__":
    mt3065 = MT3065("COM10")
    try:
        current, setpoint, upper, lower = mt3065.read_temperature_pv()
        if None not in (current, setpoint, upper, lower):
            # print(f"当前温度PV值: {current}, {setpoint}, {upper}, {lower}")
            print(f"当前温度: {current}°C, 设定温度: {setpoint}°C, 温度上限: {upper}°C, 温度下限: {lower}°C")
        else:
            print("无法读取温度PV值")
        mt3065.set_temperature(25.0)
        mt3065.start()
        time.sleep(5)
        # mt3065.stop()
    finally:
        mt3065.close()