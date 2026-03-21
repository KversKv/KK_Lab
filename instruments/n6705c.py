import time
import pyvisa

class N6705C:
    def __init__(self, resource):
        self.rm = pyvisa.ResourceManager('@py')
        if resource.startswith('TCPIP0::') or resource.startswith('USB0::'):
            self.instr = self.rm.open_resource(resource)
        else:
            self.instr = self.rm.open_resource(f'TCPIP0::{resource}::inst0::INSTR')
        self.instr.timeout = 10000
        self.instr.encoding = 'utf-8'


    def set_channel_range(self, channel):
        self.instr.write(f"SENS:CURR:RANG:AUTO ON, (@{channel})")

    def set_channel_range_off(self, channel):
        self.instr.write(f"SENS:CURR:RANG:AUTO ON, (@{channel})")

    def set_voltage(self, channel, voltage):
        # 设置电压
        # self.instr.write(f"FUNC VOLT,(@{channel})")
        self.instr.write(f"VOLT {voltage}, (@{channel})")
        # self.channel_on(channel)

    def set_mode(self, channel, mode):
        #设置模式
        #mode option: PS4Q |PS2Q |PS1Q |BATTery |CHARger |CCLoad |CVLoad |VMETer |AMETer
        self.instr.write(f"EMULation {mode},(@{channel})")
        # self.channel_on(channel)

    def set_current(self, channel, current):
        # 设置电流
        # self.instr.write(f"FUNC CURR,(@{channel})")
        self.instr.write(f"CURR {current},(@{channel})")
        # self.channel_on(channel)

    def set_current_limit(self, channel, current_limit):
        # 设置输出电流的限制
        self.instr.write(f"CURR:LIM {current_limit}, (@{channel})")
        self.instr.write(f"SENS:CURR:RANG:AUTO ON, (@{channel})")

    def set_measurement_range(self, channel, measurement_type, range_value):
        # 设置测试范围
        if measurement_type.lower() == 'voltage':
            self.instr.write(f"VOLT:RANG {range_value}, (@{channel})")
        elif measurement_type.lower() == 'current':
            self.instr.write(f"CURR:RANG {range_value}, (@{channel})")
        else:
            raise ValueError("Invalid measurement type specified. Use 'voltage' or 'current'.")

    def channel_on(self, channel):
        # 打开通道
        self.instr.write(f"OUTP ON, (@{channel})")

    def channel_off(self, channel):
        # 关闭通道
        self.instr.write(f"OUTP OFF, (@{channel})")

    def set_voltagemode(self, channel):
        # 打开通道
        self.instr.write(f"EMULation VMETer,(@{channel})")


    def measure_voltage(self, channel):
        # 测量电压
         return float(self.instr.query(f"MEAS:VOLT? (@{channel})")[:-1])

        # 假设 self.controller.instr 是 pyvisa resource（N6705C）

    def fetch_voltage(self, channel):
        # 测量电压
         return self.instr.query(f"FETC:VOLT? (@{channel})")

    def measure_voltage_fast(self, channel):
        """快速获取电压(使用FETCh命令)"""
        self.instr.write(f"INIT (@{channel})")  # 触发单次测量
        return float(self.instr.query(f"FETC:VOLT? (@{channel})"))

    def measure_current(self, channel):
        # 测量电流
        return self.instr.query(f"MEAS:CURR? (@{channel})")

    def get_current_limit(self, channel):
        # 获取电流限制
        return self.instr.query(f"CURR:LIM? (@{channel})")

    def fetch_current(self, channel):
        # 测量电流
        self.instr.write(f"INIT (@{channel})")  # 触发单次测量
        return float(self.instr.query(f"FETC:CURR? (@{channel})"))

    def arb_on(self, channel):
        # 测量电压
        return self.instr.write(f"INIT:TRAN (@{channel})")

    def arb_off(self, channel):
        # 测量电压
        return self.instr.write(f"ABOR:TRAN? (@{channel})")

    def arb_status(self, channel):
        return self.instr.query(f"STAT:OPER:COND? (@{channel})")

    def trg(self):
        return self.instr.write(f"*TRG")

    def get_average_current(self, channel, duration):
        """
        获取指定通道一段时间内的平均电流（使用Data Logger功能）

        参数:
            channel (int): 通道号 (1, 2, 3, 4)
            duration (float): 测量时长（秒）

        返回:
            float: 平均电流值
        """

        # 配置Data Logger
        self.dlog_config(channel)

        # 设置采样参数（采样率 = 1/interval）
        interval = 0.001  # 1ms采样间隔（可根据需要调整）
        points = int(duration / interval)

        # 应用采样设置
        self.instr.write(f"SENS:DLOG:TIME {duration}")
        self.instr.write(f"SENS:DLOG:PER {interval}")

        # 启动Data Logger
        self.instr.write("INIT:DLOG \"internal:\\data1.dlog\"")
        self.BUS_TRG()  # 触发开始记录

        # 等待记录完成
        time.sleep(duration + 0.5)  # 增加0.5秒缓冲时间

        # 导出数据到CSV
        self.export_file()

        # 从仪器读取CSV数据
        raw_data = self.instr.query_binary_values('MMEM:DATA? "datalog1.csv"', datatype='s')
        csv_data = raw_data[0].decode('ascii').split('\n')

        # 解析电流数据（跳过标题行）
        currents = []
        for line in csv_data[1:]:
            if line and ',' in line:
                try:
                    # CSV格式：时间,电压,电流
                    _, _, current_str = line.split(',')
                    currents.append(float(current_str))
                except (ValueError, IndexError):
                    continue

        # 计算平均值
        if currents:
            avg_current = sum(currents) / len(currents)
            return avg_current
        else:
            return 0.0

