import time
import pyvisa
from log_config import get_logger

logger = get_logger(__name__)


class N6705C:
    DLOG_PERIOD_MIN = 123e-6
    DLOG_PERIOD_MAX = 60.0

    @staticmethod
    def _clamp_dlog_period(sample_period, num_channels=1, context=""):
        required = max(float(sample_period), 20e-6 * max(int(num_channels), 1))
        if required < N6705C.DLOG_PERIOD_MIN:
            logger.warning(
                "DLOG:PER %.6fs below instrument min %.6fs (num_ch=%d%s), clamp to min",
                required, N6705C.DLOG_PERIOD_MIN, num_channels,
                f", {context}" if context else "",
            )
            return N6705C.DLOG_PERIOD_MIN
        if required > N6705C.DLOG_PERIOD_MAX:
            logger.warning(
                "DLOG:PER %.6fs above instrument max %.6fs, clamp to max",
                required, N6705C.DLOG_PERIOD_MAX,
            )
            return N6705C.DLOG_PERIOD_MAX
        return required

    def __init__(self, resource):
        logger.debug("N6705C __init__: resource=%s", resource)
        self.rm = pyvisa.ResourceManager('@py')
        if resource.startswith('TCPIP0::') or resource.startswith('USB0::'):
            self.instr = self.rm.open_resource(resource)
        else:
            self.instr = self.rm.open_resource(f'TCPIP0::{resource}::inst0::INSTR')
        self.instr.timeout = 10000
        self.instr.encoding = 'utf-8'
        logger.debug("N6705C connected, timeout=%d ms", self.instr.timeout)


    def set_channel_range(self, channel):
        self.instr.write(f"SENS:CURR:RANG:AUTO ON, (@{channel})")

    def set_channel_range_off(self, channel):
        self.instr.write(f"SENS:CURR:RANG:AUTO OFF, (@{channel})")

    def set_voltage(self, channel, voltage):
        logger.debug("N6705C set_voltage: CH%s = %s V", channel, voltage)
        self.instr.write(f"VOLT {voltage}, (@{channel})")

    def get_mode(self, channel):
        return self.instr.query(f"EMULation? (@{channel})").strip()

    def set_mode(self, channel, mode):
        logger.debug("N6705C set_mode: CH%s = %s", channel, mode)
        self.instr.write(f"EMULation {mode},(@{channel})")

    def set_current(self, channel, current):
        logger.debug("N6705C set_current: CH%s = %s A", channel, current)
        self.instr.write(f"CURR {current},(@{channel})")

    def set_current_limit(self, channel, current_limit):
        logger.debug("N6705C set_current_limit: CH%s = %s A", channel, current_limit)
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
        logger.debug("N6705C channel_on: CH%s", channel)
        self.instr.write(f"OUTP ON, (@{channel})")

    def channel_off(self, channel):
        logger.debug("N6705C channel_off: CH%s", channel)
        self.instr.write(f"OUTP OFF, (@{channel})")

    def get_channel_state(self, channel):
        result = self.instr.query(f"OUTP? (@{channel})").strip()
        return result == "1" or result.upper() == "ON"

    def set_voltagemode(self, channel):
        # 打开通道
        self.instr.write(f"EMULation VMETer,(@{channel})")


    def measure_voltage(self, channel):
        result = float(self.instr.query(f"MEAS:VOLT? (@{channel})")[:-1])
        logger.debug("N6705C measure_voltage: CH%s = %.6f V", channel, result)
        return result

    def fetch_voltage(self, channel):
        # 测量电压
         return self.instr.query(f"FETC:VOLT? (@{channel})")

    def measure_voltage_fast(self, channel):
        """快速获取电压(使用FETCh命令)"""
        self.instr.write(f"INIT (@{channel})")  # 触发单次测量
        return float(self.instr.query(f"FETC:VOLT? (@{channel})"))

    def measure_current(self, channel):
        result = float(self.instr.query(f"MEAS:CURR? (@{channel})").strip())
        logger.debug("N6705C measure_current: CH%s = %.6e A", channel, result)
        return result

    def get_current_limit(self, channel):
        # 获取电流限制
        return self.instr.query(f"CURR:LIM? (@{channel})")

    def fetch_current(self, channel):
        self.instr.write(f"INIT (@{channel})")
        result = float(self.instr.query(f"FETC:CURR? (@{channel})"))
        logger.debug("N6705C fetch_current: CH%s = %.6e A", channel, result)
        return result

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

    def clear_arb_all_channels(self, total_channels=4):
        ch_list = ",".join(str(ch) for ch in range(1, total_channels + 1))
        try:
            self.instr.write(f"ABOR:TRAN (@{ch_list})")
        except Exception:
            pass
        for ch in range(1, total_channels + 1):
            self.instr.write(f"VOLT:MODE FIX,(@{ch})")
            self.instr.write(f"CURR:MODE FIX,(@{ch})")

    def restore_arb_trigger_source(self):
        self.instr.write("TRIG:ARB:SOUR IMM")

    def arb_run(self):
        self.instr.write("TRIG:ARB:SOUR BUS")
        self.instr.write("*TRG")

    def arb_stop(self):
        self.instr.write("ABOR:TRAN")

    def test_arb_staircase(self, channel, v0=3, v1=4.3, t0=1, t1=10, t2=1, steps=500):
        logger.info("[测试] set_arb_staircase on channel %s", channel)
        logger.info("  参数: v0=%s, v1=%s, t0=%s, t1=%s, t2=%s, steps=%s", v0, v1, t0, t1, t2, steps)

        self.set_arb_staircase(channel, v0=v0, v1=v1, t0=t0, t1=t1, t2=t2, steps=steps)
        self.set_arb_continuous(channel, flag=False)
        self.arb_on(channel)
        self.channel_on(channel)
        logger.info("  ARB配置完成, 正在触发...")

        self.arb_run()
        logger.info("  ARB已触发, 等待执行...")

        total_time = t0 + t1 * (steps - 2) + t2
        time.sleep(total_time + 2)

        voltage = self.measure_voltage(channel)
        logger.info("  当前电压: %.4f V", voltage)
        logger.info("[测试] 完成")

    def read_mmem_data(self, filepath):
        import struct
        logger.debug("N6705C read_mmem_data: filepath=%s", filepath)
        old_timeout = self.instr.timeout
        old_chunk = getattr(self.instr, 'chunk_size', 20480)
        self.instr.timeout = max(old_timeout, 600000)
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
        logger.debug("N6705C disconnect called")
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

    @staticmethod
    def _interruptible_sleep(duration, on_progress=None, stop_check=None,
                             progress_start=0.0, progress_end=1.0):
        if duration <= 0:
            if on_progress:
                on_progress(progress_end)
            return
        interval = 0.5
        elapsed = 0.0
        while elapsed < duration:
            if stop_check and stop_check():
                return
            step = min(interval, duration - elapsed)
            time.sleep(step)
            elapsed += step
            if on_progress:
                frac = min(elapsed / duration, 1.0)
                on_progress(progress_start + frac * (progress_end - progress_start))

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
            sample_period = self._clamp_dlog_period(
                sample_period, num_channels=len(channels),
                context="get_current_by_datalog",
            )
            dlog_file = "internal:\\temp_dlog.dlog"
            csv_file = "internal:\\temp_dlog.csv"

            self.instr.write("*CLS")
            try:
                self.instr.write("ABOR:DLOG")
            except Exception:
                pass

            for ch in range(1, 5):
                self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                self.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

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
                             marker1_percent=10, marker2_percent=90,
                             on_progress=None, stop_check=None):
        """
        使用N6705C Datalog功能，并直接读取仪器Marker之间的平均电流

        参数:
            channels (int or list[int]): 通道号，单个int或列表
            test_time (float): 测试时间(s)
            sample_period (float): 采样周期(s)
            marker1_percent (int): marker1位置(0~100)
            marker2_percent (int): marker2位置(0~100)
            on_progress (callable|None): 进度回调 on_progress(frac), frac 0.0~1.0
            stop_check (callable|None): 返回 True 时中止

        返回:
            dict[int, float]: {通道号: marker之间平均电流}
        """
        channels = self._normalize_channels(channels)
        logger.debug("fetch_current_by_datalog: channels=%s, test_time=%s, sample_period=%s",
                     channels, test_time, sample_period)

        try:
            sample_period = self._clamp_dlog_period(
                sample_period, num_channels=len(channels),
                context="fetch_current_by_datalog",
            )
            total_points = int(test_time / sample_period)

            self.instr.write("*CLS")
            try:
                self.instr.write("ABOR:DLOG")
            except Exception:
                pass

            for ch in range(1, 5):
                self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                self.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

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

            total_wait = test_time + 1
            dlog_weight = total_wait / (total_wait + 3.0)
            self._interruptible_sleep(
                total_wait, on_progress, stop_check,
                progress_start=0.0, progress_end=dlog_weight
            )

            marker1_point = 1
            marker2_point = test_time - 1
            self.instr.write(f"SENS:DLOG:MARK1:POIN {marker1_point}")
            self.instr.write(f"SENS:DLOG:MARK2:POIN {marker2_point}")

            self._interruptible_sleep(
                2, on_progress, stop_check,
                progress_start=dlog_weight, progress_end=dlog_weight + 2.0 / (total_wait + 3.0)
            )

            result = {}
            for ch in channels:
                avg_current = float(
                    self.instr.query(f"FETC:DLOG:CURR? (@{ch})")
                )
                result[ch] = avg_current
                logger.debug("fetch_current_by_datalog: CH%s avg_current=%.6e A", ch, avg_current)

            if on_progress:
                on_progress(1.0)

            return result

        except Exception as e:
            logger.error("Error in fetch_current_by_datalog: %s", e)
            return {ch: self.fetch_current(ch) for ch in channels}

    def fetch_by_datalog(self, curr_channels, volt_channels, test_time, sample_period):
        """
        使用单次Datalog同时采集多个通道的电流和电压平均值

        参数:
            curr_channels (list[int]): 需要记录电流的通道列表
            volt_channels (list[int]): 需要记录电压的通道列表
            test_time (float): 测试时间(s)
            sample_period (float): 采样周期(s)

        返回:
            (dict[int, float], dict[int, float]):
                (电流结果 {通道号: 平均电流}, 电压结果 {通道号: 平均电压})
        """
        curr_channels = self._normalize_channels(curr_channels) if curr_channels else []
        volt_channels = self._normalize_channels(volt_channels) if volt_channels else []
        all_channels = sorted(set(curr_channels) | set(volt_channels))

        try:
            sample_period = self._clamp_dlog_period(
                sample_period,
                num_channels=len(curr_channels) + len(volt_channels),
                context="fetch_by_datalog",
            )
            self.instr.write("*CLS")
            try:
                self.instr.write("ABOR:DLOG")
            except Exception:
                pass

            for ch in range(1, 5):
                self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                self.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

            for ch in curr_channels:
                self.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                self.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")

            for ch in volt_channels:
                self.instr.write(f"SENS:DLOG:FUNC:VOLT ON,(@{ch})")

            self.instr.write(f"SENS:DLOG:TIME {test_time}")
            self.instr.write(f"SENS:DLOG:PER {sample_period}")

            self.instr.write("TRIG:DLOG:SOUR IMM")

            for ch in all_channels:
                self.channel_on(ch)

            dlog_file = "internal:\\temp_fetch.dlog"
            self.instr.write(f'INIT:DLOG "{dlog_file}"')

            time.sleep(test_time + 1)

            marker1_point = 1
            marker2_point = test_time - 1
            self.instr.write(f"SENS:DLOG:MARK1:POIN {marker1_point}")
            self.instr.write(f"SENS:DLOG:MARK2:POIN {marker2_point}")
            time.sleep(2)

            curr_result = {}
            for ch in curr_channels:
                curr_result[ch] = float(
                    self.instr.query(f"FETC:DLOG:CURR? (@{ch})")
                )

            volt_result = {}
            for ch in volt_channels:
                volt_result[ch] = float(
                    self.instr.query(f"FETC:DLOG:VOLT? (@{ch})")
                )

            return curr_result, volt_result

        except Exception as e:
            logger.error("Error in fetch_by_datalog: %s", e)
            curr_result = {}
            for ch in curr_channels:
                try:
                    curr_result[ch] = self.fetch_current(ch)
                except Exception:
                    curr_result[ch] = 0.0
            volt_result = {}
            for ch in volt_channels:
                try:
                    volt_result[ch] = float(self.measure_voltage(ch))
                except Exception:
                    volt_result[ch] = 0.0
            return curr_result, volt_result

    def prepare_force_high(self, channels, voltage_offset, current_limit,
                           monitor_channels=None):
        channels = self._normalize_channels(channels)
        logger.debug("prepare_force_high: channels=%s, voltage_offset=%s, current_limit=%s",
                     channels, voltage_offset, current_limit)
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        else:
            monitor_channels = list(monitor_channels)

        for ch in channels:
            self.set_mode(ch, "VMETer")
            self.channel_on(ch)

        time.sleep(0.5)

        measured_voltages = {}
        for ch in channels:
            measured_voltages[ch] = float(self.measure_voltage(ch))

        for ch in channels:
            new_v = measured_voltages[ch] + voltage_offset
            logger.debug("prepare_force_high: CH%s measured=%.4f V, forcing=%.4f V",
                         ch, measured_voltages[ch], new_v)
            self.set_mode(ch, "PS2Q")
            self.set_voltage(ch, new_v)
            self.set_current_limit(ch, current_limit)
            self.channel_on(ch)

        time.sleep(0.5)
        return measured_voltages

    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = N6705C._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def prepare_force_auto(self, channels, current_limit,
                           monitor_channels=None):
        channels = self._normalize_channels(channels)
        logger.debug("prepare_force_auto: channels=%s, current_limit=%s", channels, current_limit)
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        else:
            monitor_channels = list(monitor_channels)

        for ch in channels:
            self.set_mode(ch, "VMETer")
            self.channel_on(ch)

        time.sleep(0.5)

        measured_voltages = {}
        for ch in channels:
            measured_voltages[ch] = float(self.measure_voltage(ch))

        for ch in channels:
            new_v = self._align_voltage(measured_voltages[ch])
            logger.debug("prepare_force_auto: CH%s measured=%.4f V, aligned=%.4f V",
                         ch, measured_voltages[ch], new_v)
            self.set_mode(ch, "PS2Q")
            self.set_voltage(ch, new_v)
            self.set_current_limit(ch, current_limit)
            self.channel_on(ch)
            final_limit = 0.07 if new_v < 1.0 else 0.15
            self.set_current_limit(ch, final_limit)

        time.sleep(0.5)
        return measured_voltages

    def configure_datalog(self, channels, test_time, sample_period):
        channels = self._normalize_channels(channels)
        logger.debug("configure_datalog: channels=%s, test_time=%s, sample_period=%s",
                     channels, test_time, sample_period)
        sample_period = self._clamp_dlog_period(
            sample_period, num_channels=len(channels),
            context="configure_datalog",
        )
        self.instr.write("*CLS")
        try:
            self.instr.write("ABOR:DLOG")
        except Exception:
            pass
        for ch in range(1, 5):
            self.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
            self.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")
        for ch in channels:
            self.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
            self.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")
        self.instr.write(f"SENS:DLOG:TIME {test_time}")
        self.instr.write(f"SENS:DLOG:PER {sample_period}")
        self.instr.write("TRIG:DLOG:SOUR IMM")
        for ch in channels:
            self.channel_on(ch)

    def start_datalog(self, dlog_file="internal:\\temp_fetch.dlog"):
        logger.debug("start_datalog: dlog_file=%s", dlog_file)
        self.instr.write(f'INIT:DLOG "{dlog_file}"')

    def fetch_datalog_marker_results(self, channels, test_time):
        channels = self._normalize_channels(channels)
        logger.debug("fetch_datalog_marker_results: channels=%s, test_time=%s", channels, test_time)
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
            logger.debug("fetch_datalog_marker_results: CH%s avg_current=%.6e A", ch, avg_current)
        return result

    def restore_channels_to_vmeter(self, channels):
        channels = self._normalize_channels(channels)
        logger.debug("restore_channels_to_vmeter: channels=%s", channels)
        for ch in channels:
            try:
                self.set_mode(ch, "VMETer")
                self.channel_on(ch)
            except Exception:
                pass

    def force_high_and_measure(self, channels, voltage_offset, current_limit, test_time, sample_period,
                               on_progress=None, stop_check=None, monitor_channels=None):
        channels = self._normalize_channels(channels)
        logger.debug("force_high_and_measure: channels=%s, offset=%s, limit=%s, time=%s",
                     channels, voltage_offset, current_limit, test_time)
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        else:
            monitor_channels = list(monitor_channels)
        all_datalog_channels = list(channels) + [ch for ch in monitor_channels if ch not in channels]
        original_modes = {}
        original_voltages = {}

        setup_time = 1.0
        datalog_est = test_time + 4.0
        total_est = setup_time + datalog_est
        if total_est <= 0:
            total_est = 1.0

        def _sub_progress(frac):
            if on_progress:
                on_progress((setup_time + frac * datalog_est) / total_est)

        try:
            for ch in channels:
                original_modes[ch] = self.get_mode(ch)
                self.set_mode(ch, "VMETer")
                self.channel_on(ch)

            self._interruptible_sleep(0.5, on_progress, stop_check,
                                      progress_start=0.0, progress_end=0.25 * setup_time / total_est)

            measured_voltages = {}
            for ch in channels:
                measured_voltages[ch] = float(self.measure_voltage(ch))

            for ch in channels:
                new_v = measured_voltages[ch] + voltage_offset
                original_voltages[ch] = new_v
                self.set_mode(ch, "PS2Q")
                self.set_voltage(ch, new_v)
                self.set_current_limit(ch, current_limit)
                self.channel_on(ch)

            self._interruptible_sleep(0.5, on_progress, stop_check,
                                      progress_start=0.5 * setup_time / total_est,
                                      progress_end=setup_time / total_est)

            curr_result = self.fetch_current_by_datalog(
                all_datalog_channels, test_time, sample_period,
                on_progress=_sub_progress, stop_check=stop_check,
            )

            for ch in channels:
                self.set_mode(ch, "VMETer")
                self.channel_on(ch)

            if on_progress:
                on_progress(1.0)

            return curr_result, measured_voltages

        except Exception as e:
            logger.error("Error in force_high_and_measure: %s", e)
            for ch in channels:
                try:
                    self.set_mode(ch, "VMETer")
                    self.channel_on(ch)
                except Exception:
                    pass
            raise


if __name__ == "__main__":
    IP = "192.168.3.99"
    CHANNEL = 1

    n6705c = N6705C(IP)
    try:
        idn = n6705c.instr.query("*IDN?").strip()
        logger.info("已连接: %s", idn)
        n6705c.test_arb_staircase(CHANNEL)
    finally:
        n6705c.disconnect()
        logger.info("已断开连接")

