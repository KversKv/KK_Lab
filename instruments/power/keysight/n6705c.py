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

    def get_mode(self, channel):
        return self.instr.query(f"EMULation? (@{channel})").strip()

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
        self.instr.write(f"CURR:LIM {current_limit}, (@{channel})")
        self.instr.write(f"SENS:CURR:RANG:AUTO ON, (@{channel})")

    def set_voltage_limit(self, channel, voltage_limit):
        self.instr.write(f"VOLT:LIM {voltage_limit}, (@{channel})")

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

    def get_channel_state(self, channel):
        result = self.instr.query(f"OUTP? (@{channel})").strip()
        return result == "1" or result.upper() == "ON"

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
        return self.instr.write(f"INIT:TRAN (@{channel})")

    def arb_off(self, channel):
        return self.instr.write(f"ABOR:TRAN? (@{channel})")

    def arb_status(self, channel):
        return self.instr.query(f"STAT:OPER:COND? (@{channel})")

    def trg(self):
        return self.instr.write(f"*TRG")

    def set_arb_type(self, channel, arb_type="VOLT"):
        self.instr.write(f"ARB:FUNC:TYPE {arb_type},(@{channel})")

    def set_arb_step(self, channel, v0, v1, t0, t1):
        """
        配置ARB阶跃波形 (Step Shape)

        参数:
            channel (int): 通道号
            v0 (float): 起始电压(V)
            v1 (float): 终止电压(V)
            t0 (float): 起始电压保持时间(s)
            t1 (float): 终止电压保持时间(s)
        """
        self.instr.write(f"ARB:FUNC:TYPE VOLT,(@{channel})")
        self.instr.write(f"ARB:FUNC:SHAP STEP,(@{channel})")
        self.instr.write(f"ARB:VOLT:STEP:STAR {v0},(@{channel})")
        self.instr.write(f"ARB:VOLT:STEP:END {v1},(@{channel})")
        self.instr.write(f"ARB:VOLT:STEP:STAR:TIM {t0},(@{channel})")
        self.instr.write(f"ARB:VOLT:STEP:END:TIM {t1},(@{channel})")
        self.instr.write(f"VOLT:MODE ARB,(@{channel})")

    def set_arb_staircase(self, channel, v0, v1, t0, t1, t2, steps):
        """
        配置ARB阶梯波形 (Staircase Shape)

        参数:
            channel (int): 通道号
            v0 (float): 起始电压(V)
            v1 (float): 终止电压(V)
            t0 (float): 阶梯之前的保持时间(s)
            t1 (float): 阶梯变化持续时间(s)
            t2 (float): 阶梯之后的保持时间(s)
            steps (int): 阶梯数量
        """
        self.instr.write(f"ARB:FUNC:TYPE VOLT,(@{channel})")
        self.instr.write(f"ARB:FUNC:SHAP STA,(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:STAR {v0},(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:END {v1},(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:STAR:TIM {t0},(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:TIM {t1},(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:END:TIM {t2},(@{channel})")
        self.instr.write(f"ARB:VOLT:STA:NST {steps},(@{channel})")
        self.instr.write(f"VOLT:MODE ARB,(@{channel})")

    def set_arb_pulse(self, channel, v0, v1, t0, t1, t2, frequency):
        """
        配置ARB脉冲波形 (Pulse Shape)

        参数:
            channel (int): 通道号
            v0 (float): 基准电压(V)
            v1 (float): 脉冲顶部电压(V)
            t0 (float): 起始保持时间(s)
            t1 (float): 终止保持时间(s)
            t2 (float): 脉冲顶部持续时间(s)
            frequency (float): 脉冲频率(Hz)
        """
        self.instr.write(f"ARB:FUNC:TYPE VOLT,(@{channel})")
        self.instr.write(f"ARB:FUNC:SHAP PULS,(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:STAR {v0},(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:TOP {v1},(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:STAR:TIM {t0},(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:END:TIM {t1},(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:TOP:TIM {t2},(@{channel})")
        self.instr.write(f"ARB:VOLT:PULS:FREQ {frequency},(@{channel})")
        self.instr.write(f"VOLT:MODE ARB,(@{channel})")

    def set_arb_continuous(self, channel, flag=False):
        if flag:
            self.instr.write(f"ARB:TERM:LAST ON,(@{channel})")
        else:
            self.instr.write(f"ARB:TERM:LAST OFF,(@{channel})")

    def arb_run(self):
        self.instr.write("TRIG:ARB:SOUR BUS")
        self.instr.write("*TRG")

    def arb_stop(self):
        self.instr.write("ABOR:TRAN")

    def test_arb_staircase(self, channel, v0=3, v1=4.3, t0=1, t1=10, t2=1, steps=500):
        print(f"[测试] set_arb_staircase on channel {channel}")
        print(f"  参数: v0={v0}, v1={v1}, t0={t0}, t1={t1}, t2={t2}, steps={steps}")

        self.set_arb_staircase(channel, v0=v0, v1=v1, t0=t0, t1=t1, t2=t2, steps=steps)
        self.set_arb_continuous(channel, flag=False)
        self.arb_on(channel)
        self.channel_on(channel)
        print("  ARB配置完成, 正在触发...")

        self.arb_run()
        print("  ARB已触发, 等待执行...")

        total_time = t0 + t1 * (steps - 2) + t2
        time.sleep(total_time + 2)

        voltage = self.measure_voltage(channel)
        print(f"  当前电压: {voltage:.4f} V")
        print("[测试] 完成")

    def read_mmem_data(self, filepath):
        import struct
        old_timeout = self.instr.timeout
        old_chunk = getattr(self.instr, 'chunk_size', 20480)
        self.instr.timeout = 300000
        self.instr.chunk_size = 1024 * 1024

        try:
            self.instr.write(f'MMEM:DATA? "{filepath}"')

            hash_char = self.instr.read_bytes(1)
            if hash_char != b'#':
                rest = self.instr.read_raw()
                return (hash_char + rest).decode('ascii', errors='replace')

            digit_count_byte = self.instr.read_bytes(1)
            digit_count = int(digit_count_byte.decode('ascii'))
            data_len_bytes = self.instr.read_bytes(digit_count)
            data_len = int(data_len_bytes.decode('ascii'))

            raw_data = b""
            remaining = data_len
            while remaining > 0:
                read_size = min(remaining, 1024 * 1024)
                chunk = self.instr.read_bytes(read_size)
                raw_data += chunk
                remaining -= len(chunk)

            try:
                self.instr.read_bytes(1)
            except Exception:
                pass

            return raw_data
        finally:
            self.instr.timeout = old_timeout
            self.instr.chunk_size = old_chunk

    def disconnect(self):
        """
        断开与仪器的连接
        """
        if self.instr is not None:
            try:
                self.instr.close()
            except Exception:
                pass
            self.instr = None
        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None
    
    def format_current(self, current_A):
        """
        将电流(A)格式化为人类易读单位字符串
        """
        abs_i = abs(current_A)

        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def _normalize_channels(self, channels):
        if isinstance(channels, int):
            return [channels]
        return list(channels)

    def _channel_list_str(self, channels):
        return ",".join(str(ch) for ch in channels)

    def get_average_current(self, channels, duration):
        """
        获取指定通道一段时间内的平均电流（使用Data Logger功能）

        参数:
            channels (int or list[int]): 通道号，单个int或列表 如 1 或 [1,2,3]
            duration (float): 测量时长（秒）

        返回:
            dict[int, float]: {通道号: 平均电流值}
        """
        channels = self._normalize_channels(channels)
        ch_str = self._channel_list_str(channels)

        for ch in channels:
            self.dlog_config(ch)

        interval = 0.001
        self.instr.write(f"SENS:DLOG:TIME {duration}")
        self.instr.write(f"SENS:DLOG:PER {interval}")

        self.instr.write("INIT:DLOG \"internal:\\data1.dlog\"")
        self.BUS_TRG()

        time.sleep(duration + 0.5)

        self.export_file()

        raw_data = self.instr.query_binary_values('MMEM:DATA? "datalog1.csv"', datatype='s')
        csv_data = raw_data[0].decode('ascii').split('\n')

        channel_currents = {ch: [] for ch in channels}
        for line in csv_data[1:]:
            if line and ',' in line:
                try:
                    parts = line.split(',')
                    for i, ch in enumerate(channels):
                        col_idx = 1 + i * 2 + 1
                        channel_currents[ch].append(float(parts[col_idx]))
                except (ValueError, IndexError):
                    continue

        result = {}
        for ch in channels:
            currents = channel_currents[ch]
            result[ch] = sum(currents) / len(currents) if currents else 0.0
        return result

    def get_current_by_datalog(self, channels, test_time, sample_period,
                           marker1_percent=10, marker2_percent=90):
        """
        使用Datalog采集并通过CSV解析获取Marker区间内的平均电流

        参数:
            channels (int or list[int]): 通道号，单个int或列表
            test_time (float): 测试时间(s)
            sample_period (float): 采样周期(s)
            marker1_percent (int): marker1位置百分比(0~100)
            marker2_percent (int): marker2位置百分比(0~100)

        返回:
            dict[int, float]: {通道号: marker区间平均电流}
        """
        channels = self._normalize_channels(channels)
        ch_str = self._channel_list_str(channels)

        try:
            dlog_file = "internal:\\temp_dlog.dlog"
            csv_file = "internal:\\temp_dlog.csv"

            for ch in range(1, 5):
                self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")

            for ch in channels:
                self.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                self.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")

            self.instr.write(f"SENS:DLOG:TIME {test_time}")
            self.instr.write(f"SENS:DLOG:PER {sample_period}")

            self.instr.write("TRIG:DLOG:SOUR IMM")

            for ch in channels:
                self.channel_on(ch)

            self.instr.write(f'INIT:DLOG "{dlog_file}"')

            time.sleep(test_time + 2)

            self.instr.write(f'MMEM:EXP:DLOG "{csv_file}"')
            time.sleep(3)

            self.instr.write("FORM ASC")
            raw = self.instr.query(f'MMEM:DATA? "{csv_file}"')

            lines = raw.splitlines()

            channel_data = {ch: [] for ch in channels}
            for line in lines:
                if "," in line:
                    parts = line.split(",")
                    try:
                        for i, ch in enumerate(channels):
                            col_idx = 1 + i
                            channel_data[ch].append(float(parts[col_idx]))
                    except (ValueError, IndexError):
                        pass

            result = {}
            for ch in channels:
                data = channel_data[ch]
                if not data:
                    result[ch] = self.fetch_current(ch)
                    continue

                total_points = len(data)
                m1 = max(0, int(total_points * marker1_percent / 100))
                m2 = min(total_points - 1, int(total_points * marker2_percent / 100))
                marker_data = data[m1:m2]
                result[ch] = sum(marker_data) / len(marker_data) if marker_data else 0.0

            return result

        except Exception as e:
            return {ch: self.fetch_current(ch) for ch in channels}

    def fetch_current_by_datalog(self, channels, test_time, sample_period,
                             marker1_percent=10, marker2_percent=90):
        """
        使用N6705C Datalog功能，并直接读取仪器Marker之间的平均电流

        参数:
            channels (int or list[int]): 通道号，单个int或列表
            test_time (float): 测试时间(s)
            sample_period (float): 采样周期(s)
            marker1_percent (int): marker1位置(0~100)
            marker2_percent (int): marker2位置(0~100)

        返回:
            dict[int, float]: {通道号: marker之间平均电流}
        """
        channels = self._normalize_channels(channels)

        try:
            total_points = int(test_time / sample_period)

            self.instr.write("*CLS")

            for ch in range(1, 5):
                self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")

            for ch in channels:
                self.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                self.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")

            self.instr.write(f"SENS:DLOG:TIME {test_time}")
            self.instr.write(f"SENS:DLOG:PER {sample_period}")

            self.instr.write("TRIG:DLOG:SOUR IMM")

            for ch in channels:
                self.channel_on(ch)

            dlog_file = "internal:\\temp_fetch.dlog"
            self.instr.write(f'INIT:DLOG "{dlog_file}"')

            time.sleep(test_time + 1)

            marker1_point = 1
            marker2_point = test_time - 1
            self.instr.write(f"SENS:DLOG:MARK1:POIN {marker1_point}")
            self.instr.write(f"SENS:DLOG:MARK2:POIN {marker2_point}")
            time.sleep(2)

            result = {}
            for ch in channels:
                avg_current = float(
                    self.instr.query(f"FETC:DLOG:CURR? (@{ch})")
                )
                result[ch] = avg_current

            return result

        except Exception as e:
            print(f"Error in fetch_current_by_datalog: {e}")
            return {ch: self.fetch_current(ch) for ch in channels}


if __name__ == "__main__":
    IP = "192.168.3.99"
    CHANNEL = 1

    n6705c = N6705C(IP)
    try:
        idn = n6705c.instr.query("*IDN?").strip()
        print(f"已连接: {idn}")
        n6705c.test_arb_staircase(CHANNEL)
    finally:
        n6705c.disconnect()
        print("已断开连接")

