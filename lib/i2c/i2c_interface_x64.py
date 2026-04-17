#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I2C读写接口封装类

封装了I2C接口的读写操作，提供简洁的API接口
支持8位、10位、32位地址/数据宽度的操作

作者: 芯片调试工具
创建时间: 2025
"""

import sys
import time
import threading
from pathlib import Path


script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from Bes_I2CIO_Interface import (
    BESI2CIO, I2CSpeedMode, I2CWidthFlag,
    I2CError, I2CDeviceError, I2COperationError, I2CParameterError, I2CStatus,
)

import logging
logger = logging.getLogger(__name__)

_INT_TO_WIDTH_FLAG = {
    8: I2CWidthFlag.BIT_8,
    10: I2CWidthFlag.BIT_10,
    32: I2CWidthFlag.BIT_32,
}


class I2CInterface:
    """I2C接口封装类，提供简洁的I2C操作API"""

    _init_lock = threading.Lock()

    def __init__(self, dll_path=None, speed_mode=I2CSpeedMode.SPEED_100K,
                 verbose=False):
        """
        初始化I2C接口

        参数:
        dll_path: I2C接口DLL文件路径，如果为None则使用默认路径
        speed_mode: I2C通信速度模式，默认100kHz
        verbose: 是否显示DLL内部调试输出，默认False
        """
        self._speed_mode = speed_mode
        self._verbose = verbose

        if dll_path is None:
            dll_path = str(script_dir / "config" / "BES_USBIO_I2C_X64.dll")

        self._dll_path = dll_path
        self._i2c: BESI2CIO | None = None
        self._initialized = False

    @property
    def speed_mode(self) -> I2CSpeedMode:
        return self._speed_mode

    @speed_mode.setter
    def speed_mode(self, value: I2CSpeedMode):
        self._speed_mode = value

    @property
    def initialized(self) -> bool:
        return self._initialized

    def config(self, dll_path=None, speed_mode=None):
        """
        配置I2C接口参数

        参数:
        dll_path: I2C接口DLL文件路径（修改后需重新初始化）
        speed_mode: I2C通信速度模式（仅更新参数，不触发重新初始化）
        """
        need_reinit = False

        if speed_mode is not None:
            self._speed_mode = speed_mode

        if dll_path is not None and dll_path != self._dll_path:
            self._dll_path = dll_path
            need_reinit = True

        if need_reinit and self._initialized:
            old_i2c = self._i2c
            try:
                self.initialize()
            except Exception:
                self._i2c = old_i2c
                self._initialized = old_i2c is not None
                raise

    def initialize(self):
        """初始化I2C接口"""
        try:
            self._i2c = BESI2CIO(self._dll_path, verbose=self._verbose)
            self._initialized = True
            return True
        except Exception as e:
            logger.error("I2C接口初始化失败: %s", e)
            self._initialized = False
            return False

    def _ensure_initialized(self):
        if self._initialized:
            return
        with self._init_lock:
            if not self._initialized:
                if not self.initialize():
                    raise I2CDeviceError(
                        I2CStatus.ERROR_OPEN_DEVICE, "I2C接口未初始化成功"
                    )

    @staticmethod
    def _normalize_width_flag(width_flag):
        if isinstance(width_flag, I2CWidthFlag):
            return width_flag
        if width_flag in _INT_TO_WIDTH_FLAG:
            return _INT_TO_WIDTH_FLAG[width_flag]
        try:
            return I2CWidthFlag(width_flag)
        except ValueError:
            raise ValueError(f"Invalid width_flag: {width_flag}")

    def read(self, device_addr, reg_addr, width_flag):
        """
        从I2C设备读取数据

        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        width_flag: 位宽标志（I2CWidthFlag 或 整数 8/10/32）

        返回:
        读取到的数据

        异常:
        I2CDeviceError: 设备打开或连接失败
        I2COperationError: I2C通信操作失败
        I2CParameterError: 参数无效
        ValueError: width_flag 值非法
        """
        self._ensure_initialized()
        width_flag = self._normalize_width_flag(width_flag)
        return self._i2c.read(
            self._speed_mode,
            device_addr,
            reg_addr,
            width_flag,
        )

    def write(self, device_addr, reg_addr, write_data, width_flag):
        """
        向I2C设备写入数据

        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        write_data: 要写入的数据
        width_flag: 位宽标志（I2CWidthFlag 或 整数 8/10/32）

        异常:
        I2CDeviceError: 设备打开或连接失败
        I2COperationError: I2C通信操作失败
        I2CParameterError: 参数无效
        ValueError: width_flag 值非法
        """
        self._ensure_initialized()
        width_flag = self._normalize_width_flag(width_flag)
        self._i2c.write(
            self._speed_mode,
            device_addr,
            reg_addr,
            write_data,
            width_flag,
        )
        return True

    def _safe_read(self, device_addr, reg_addr, width_flag):
        try:
            return self.read(device_addr, reg_addr, width_flag)
        except (I2CError, Exception) as e:
            logger.debug("读取失败 device=0x%02X reg=0x%08X width=%s: %s",
                         device_addr, reg_addr, width_flag, e)
            return None

    @staticmethod
    def _is_valid_i2c_value(val):
        return val is not None and val != 0xFFFF and val != 0xFFFFFFFF

    @staticmethod
    def _version_letter(ver_num):
        return chr(ord('A') + ver_num) if 0 <= ver_num <= 25 else "?"

    @staticmethod
    def _parse_chip_model(raw_32bit):
        chip_num = raw_32bit & 0xFFFF
        suffix_byte = (raw_32bit >> 16) & 0xFF
        version_byte = (raw_32bit >> 24) & 0xFF
        model = "%X" % chip_num
        if 0x20 < suffix_byte < 0x7F:
            model += chr(suffix_byte)
        return model, version_byte

    _NEWGEN_PMU_MARKER = 0xF

    @staticmethod
    def _parse_pmu_id(raw_16bit):
        """
        解析PMU 16bit寄存器值

        编码规则 (0xHHNV):
            HH   — 高字节，型号前缀（十六进制表示）
            N    — 低字节高4位，型号子序号（hex数字值作十进制）
                   当 N == 0xF 时，表示新一代PMU，需额外读取扩展寄存器
            V    — 低字节低4位，版本号（0→A, 1→B, 2→C, ...）

        示例:
            0x18D0 → PMU1813, verA
            0x1891 → PMU1809, verB
            0x18A2 → PMU1810, verC
            0x18F0 → 新一代PMU标记，需读取扩展寄存器
        """
        high_byte = (raw_16bit >> 8) & 0xFF
        sub_num = (raw_16bit >> 4) & 0xF
        ver_num = raw_16bit & 0xF
        model = "%02X%d" % (high_byte, sub_num)
        return model, ver_num, sub_num == I2CInterface._NEWGEN_PMU_MARKER

    @staticmethod
    def _parse_newgen_pmu_ext(prefix_hex, raw_ext_16bit):
        """
        解析新一代PMU扩展寄存器值 (reg=0x0001)

        编码规则:
            [15:8] — 型号后两位编码（十六进制表示）
            [7:0]  — 后缀字母ASCII码（0x00表示无后缀）

        示例:
            prefix="18", ext=0x0650 → "1806P"
        """
        tail_num = (raw_ext_16bit >> 8) & 0xFF
        suffix_byte = raw_ext_16bit & 0xFF
        model = "%s%02X" % (prefix_hex, tail_num)
        if 0x20 < suffix_byte < 0x7F:
            model += chr(suffix_byte)
        return model

    def bes_chip_check(self):
        """
        BES芯片检测函数

        地址定义:
            0x11 — mainDie（Main-die，32bit模式）
            0x27 — mainDie_pmu（Main-die内置PMU）
            0x17 — PMU（独立PMU芯片）

        芯片型号解析 (device=0x11, reg=0x40080000, 32bit):
            bit[15:0]  — 芯片序号（如 0x1605 → "1605"）
            bit[23:16] — 后缀字母ASCII码（如 0x50 → 'P'，0x00 → 无后缀）
            bit[31:24] — 版本号（0→verA, 1→verB, ...）

        Main-die内置PMU / 独立PMU ID解析 (16bit, 0xHHNV):
            HH  — 高字节，型号前缀（十进制）
            N   — 低字节高4位，型号子序号（hex值作十进制）
            V   — 低字节低4位，版本号（0→verA, 1→verB, 2→verC, ...）
            示例: 0x18D0 → PMU1813/verA, 0x1891 → PMU1809/verB

        Main-die内置PMU检测 (device=0x27):
            优先检查10bit，若读取值有效(≠0xFFFF)则为10bit，否则检查8bit
            型号名为 "BES" + 解析后的PMU ID

        独立PMU检测 (device=0x17):
            优先检查10bit，若读取值有效(≠0xFFFF)则为10bit，否则检查8bit
            型号名为 "PMU" + 解析后的PMU ID
            当N==0xF（新一代PMU）时，额外读取reg=0x0001:
                [15:8] — 型号后两位编码, [7:0] — 后缀字母ASCII码
                示例: 0x0000=0x18F0, 0x0001=0x0650 → PMU1806P

        返回:
        dict: 包含以下字段的字典（与 CHIP_CONFIG 字段名一致）
            - chip_name: 芯片名称，如 "bes1605" (str | None)
            - main_die: Main-die型号，如 "BES1605" (str | None)
            - main_die_version: Main-die版本，如 "verA" (str | None)
            - main_die_i2c_width: Main-die I2C位宽 (32 | None)
            - main_die_i2c_addr: Main-die I2C设备地址 (int | None)
            - main_die_pmu: Main-die内置PMU型号，如 "BES1813" (str | None)
            - main_die_pmu_version: Main-die内置PMU版本，如 "verA" (str | None)
            - main_die_pmu_i2c_width: Main-die内置PMU I2C位宽 (8 | 10 | None)
            - main_die_pmu_i2c_addr: Main-die内置PMU I2C设备地址 (int | None)
            - has_pmu: 是否有独立PMU芯片 (bool)
            - pmu: PMU型号，如 "PMU1813" (str | None)
            - pmu_version: PMU版本，如 "verA" (str | None)
            - pmu_i2c_width: PMU I2C位宽 (8 | 10 | None)
            - pmu_i2c_addr: PMU I2C设备地址 (int | None)
        """
        self._ensure_initialized()

        val_0x27_8bit = self._safe_read(0x27, 0x0000, I2CWidthFlag.BIT_8)
        val_0x27_10bit = self._safe_read(0x27, 0x0000, I2CWidthFlag.BIT_10)
        val_0x17_8bit = self._safe_read(0x17, 0x0000, I2CWidthFlag.BIT_8)
        val_0x17_10bit = self._safe_read(0x17, 0x0000, I2CWidthFlag.BIT_10)
        val_0x11_32bit = self._safe_read(0x11, 0x40080000, I2CWidthFlag.BIT_32)

        logger.debug("bes_chip_check 读取结果:")
        logger.debug("  [mainDie_pmu] device=0x27, reg=0x0000, 8bit  => %s",
                      "0x%04X" % val_0x27_8bit if val_0x27_8bit is not None else "None")
        logger.debug("  [mainDie_pmu] device=0x27, reg=0x0000, 10bit => %s",
                      "0x%04X" % val_0x27_10bit if val_0x27_10bit is not None else "None")
        logger.debug("  [PMU]         device=0x17, reg=0x0000, 8bit  => %s",
                      "0x%04X" % val_0x17_8bit if val_0x17_8bit is not None else "None")
        logger.debug("  [PMU]         device=0x17, reg=0x0000, 10bit => %s",
                      "0x%04X" % val_0x17_10bit if val_0x17_10bit is not None else "None")
        logger.debug("  [mainDie]     device=0x11, reg=0x40080000, 32bit => %s",
                      "0x%08X" % val_0x11_32bit if val_0x11_32bit is not None else "None")

        chip_name = None
        main_die = None
        main_die_version = None
        main_die_i2c_width = None
        main_die_i2c_addr = None
        main_die_pmu = None
        main_die_pmu_version = None
        main_die_pmu_i2c_width = None
        main_die_pmu_i2c_addr = None
        has_pmu = False
        pmu = None
        pmu_version = None
        pmu_i2c_width = None
        pmu_i2c_addr = None

        if self._is_valid_i2c_value(val_0x11_32bit):
            model, ver_byte = self._parse_chip_model(val_0x11_32bit)
            chip_name = "bes%s" % model.lower()
            main_die = "BES%s" % model
            main_die_version = "ver%s" % self._version_letter(ver_byte)
            main_die_i2c_width = 32
            main_die_i2c_addr = 0x11

        if self._is_valid_i2c_value(val_0x27_10bit):
            main_die_pmu_i2c_width = 10
            main_die_pmu_i2c_addr = 0x27
            main_die_pmu = "BES%X" % val_0x27_10bit
        elif self._is_valid_i2c_value(val_0x27_8bit):
            main_die_pmu_i2c_width = 8
            main_die_pmu_i2c_addr = 0x27
            main_die_pmu = "BES%X" % val_0x27_8bit

        if self._is_valid_i2c_value(val_0x17_10bit):
            has_pmu = True
            pmu_i2c_width = 10
            pmu_i2c_addr = 0x17
            pmu_model, pmu_ver, is_newgen = self._parse_pmu_id(val_0x17_10bit)
            if is_newgen:
                ext_val = self._safe_read(0x17, 0x0001, I2CWidthFlag.BIT_10)
                logger.debug("  [PMU newgen]  device=0x17, reg=0x0001, 10bit => %s",
                              "0x%04X" % ext_val if ext_val is not None else "None")
                if ext_val is not None:
                    prefix_hex = "%02X" % ((val_0x17_10bit >> 8) & 0xFF)
                    pmu_model = self._parse_newgen_pmu_ext(prefix_hex, ext_val)
            pmu = "PMU%s" % pmu_model
            pmu_version = "ver%s" % self._version_letter(pmu_ver)
        elif self._is_valid_i2c_value(val_0x17_8bit):
            has_pmu = True
            pmu_i2c_width = 8
            pmu_i2c_addr = 0x17
            pmu_model, pmu_ver, is_newgen = self._parse_pmu_id(val_0x17_8bit)
            if is_newgen:
                ext_val = self._safe_read(0x17, 0x0001, I2CWidthFlag.BIT_8)
                logger.debug("  [PMU newgen]  device=0x17, reg=0x0001, 8bit  => %s",
                              "0x%04X" % ext_val if ext_val is not None else "None")
                if ext_val is not None:
                    prefix_hex = "%02X" % ((val_0x17_8bit >> 8) & 0xFF)
                    pmu_model = self._parse_newgen_pmu_ext(prefix_hex, ext_val)
            pmu = "PMU%s" % pmu_model
            pmu_version = "ver%s" % self._version_letter(pmu_ver)

        result = {
            "chip_name": chip_name,
            "main_die": main_die,
            "main_die_version": main_die_version,
            "main_die_i2c_width": main_die_i2c_width,
            "main_die_i2c_addr": main_die_i2c_addr,
            "main_die_pmu": main_die_pmu,
            "main_die_pmu_version": main_die_pmu_version,
            "main_die_pmu_i2c_width": main_die_pmu_i2c_width,
            "main_die_pmu_i2c_addr": main_die_pmu_i2c_addr,
            "has_pmu": has_pmu,
            "pmu": pmu,
            "pmu_version": pmu_version,
            "pmu_i2c_width": pmu_i2c_width,
            "pmu_i2c_addr": pmu_i2c_addr,
        }

        logger.debug("bes_chip_check 检测结果:")
        logger.debug("  chip_name: %s", result["chip_name"])
        logger.debug("  main_die: %s", result["main_die"])
        logger.debug("  main_die_version: %s", result["main_die_version"])
        logger.debug("  main_die_i2c_width: %s", result["main_die_i2c_width"])
        logger.debug("  main_die_i2c_addr: %s",
                      "0x%02X" % result["main_die_i2c_addr"] if result["main_die_i2c_addr"] is not None else "None")
        logger.debug("  main_die_pmu: %s", result["main_die_pmu"])
        logger.debug("  main_die_pmu_version: %s", result["main_die_pmu_version"])
        logger.debug("  main_die_pmu_i2c_width: %s", result["main_die_pmu_i2c_width"])
        logger.debug("  main_die_pmu_i2c_addr: %s",
                      "0x%02X" % result["main_die_pmu_i2c_addr"] if result["main_die_pmu_i2c_addr"] is not None else "None")
        logger.debug("  has_pmu: %s", result["has_pmu"])
        logger.debug("  pmu: %s", result["pmu"])
        logger.debug("  pmu_version: %s", result["pmu_version"])
        logger.debug("  pmu_i2c_width: %s", result["pmu_i2c_width"])
        logger.debug("  pmu_i2c_addr: %s",
                      "0x%02X" % result["pmu_i2c_addr"] if result["pmu_i2c_addr"] is not None else "None")

        return result

    @property
    def raw(self) -> BESI2CIO:
        """获取底层I2C对象，用于高级操作（如 read_data / write_data）"""
        self._ensure_initialized()
        return self._i2c

    def close(self):
        """释放I2C接口资源"""
        self._i2c = None
        self._initialized = False

    def __enter__(self):
        self._ensure_initialized()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# 示例用法
if __name__ == "__main__":
    """示例用法演示"""
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    logger.info("I2C接口封装类示例")
    logger.info("=" * 50)
    
    # 创建I2C接口实例
    i2c = I2CInterface()
    
    # 配置参数（可选，如果使用默认参数则不需要）
    # i2c.config(speed_mode=I2CSpeedMode.SPEED_400K)
    
    # 测试参数
    device_addr = 0x17
    width_flag = I2CWidthFlag.BIT_10
    
    try:
        # 0. 芯片检测
        logger.info("0. BES芯片检测：")
        chip_info = i2c.bes_chip_check()
        logger.info("   检测结果: %s", chip_info)
        logger.info("")

        # # 1. 读取操作：器件地址0x17，寄存器地址0x0000
        # reg_addr_read = 0x0000
        # logger.info("1. 读取操作：")
        # logger.info("   设备地址: 0x%02X", device_addr)
        # logger.info("   寄存器地址: 0x%04X", reg_addr_read)
        # logger.info("   位宽模式: %s", width_flag.name)
        
        # read_data = i2c.read(device_addr, reg_addr_read, width_flag)
        # logger.info("   读取结果: 0x%04X", read_data)
        
        # reg_addr_write = 0x1e7
        # write_data = 0x20AA
        # logger.info("2. 写入操作：")
        # logger.info("   设备地址: 0x%02X", device_addr)
        # logger.info("   寄存器地址: 0x%04X", reg_addr_write)
        # logger.info("   写入数据: 0x%04X", write_data)
        # logger.info("   位宽模式: %s", width_flag.name)
        
        # i2c.write(device_addr, reg_addr_write, write_data, width_flag)
        # logger.info("   写入成功")
        
        # time.sleep(0.1)
        # verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
        # logger.info("3. 验证写入结果：")
        # logger.info("   寄存器地址0x%04X的当前值: 0x%04X", reg_addr_write, verify_data)
        # logger.info("   验证%s", '成功' if verify_data == write_data else '失败')
        
    except Exception as e:
        logger.error("I2C操作失败: %s", e)