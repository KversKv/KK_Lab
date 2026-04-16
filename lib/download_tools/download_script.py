#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DUT UART下载工具封装

封装dldtool.exe的命令行调用，提供Python API接口
支持Flash烧录、Ramrun、擦除扇区、擦除整片、读写eFuse等操作
"""

import re
import subprocess
import threading
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Union, Callable

logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent
DLDTOOL_EXE = TOOLS_DIR / "dldtool.exe"

TAIL_SCAN_SIZE = 1024
CHIP_PATTERN = re.compile(rb"CHIP=best(\w+)")


class DownloadState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    WAITING_SYNC = "waiting_sync"
    SYNCING = "syncing"
    PROGRAMMING = "programming"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class DownloadResult:
    success: bool = False
    state: DownloadState = DownloadState.IDLE
    returncode: Optional[int] = None
    output_lines: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


def detect_chip_from_bin(bin_path: Union[str, Path]) -> Optional[str]:
    """
    从BIN文件尾部解析芯片型号

    BIN尾部包含形如 "CHIP=best1307ph" 的信息，
    提取后返回芯片型号字符串(如 "1307ph")

    参数:
        bin_path: BIN文件路径

    返回:
        芯片型号字符串，未找到返回None
    """
    bin_path = Path(bin_path)
    if not bin_path.exists():
        logger.warning("BIN文件不存在: %s", bin_path)
        return None
    file_size = bin_path.stat().st_size
    scan_size = min(TAIL_SCAN_SIZE, file_size)
    with open(bin_path, "rb") as f:
        f.seek(-scan_size, 2)
        tail = f.read()
    m = CHIP_PATTERN.search(tail)
    if m:
        chip = m.group(1).decode("ascii")
        logger.info("从BIN文件 %s 检测到芯片型号: %s", bin_path.name, chip)
        return chip
    logger.warning("未能从BIN文件 %s 尾部检测到CHIP信息", bin_path.name)
    return None


def match_programmer(chip: str) -> Optional[Path]:
    """
    根据芯片型号匹配对应的programmer文件

    参数:
        chip: 芯片型号(如 "1307ph")

    返回:
        匹配到的programmer文件路径，未找到返回None
    """
    programmer_name = f"programmer{chip}.bin"
    programmer_path = TOOLS_DIR / programmer_name
    if programmer_path.exists():
        logger.info("匹配到programmer文件: %s", programmer_name)
        return programmer_path
    logger.warning("未找到匹配的programmer文件: %s", programmer_name)
    return None


def auto_detect_programmer(bin_path: Union[str, Path]) -> Optional[Path]:
    """
    从待下载BIN文件自动识别并匹配programmer

    参数:
        bin_path: 待下载BIN文件路径

    返回:
        匹配到的programmer文件路径，未找到返回None
    """
    chip = detect_chip_from_bin(bin_path)
    if chip is None:
        return None
    return match_programmer(chip)


class DownloadMode(Enum):
    FLASH = "flash"
    RAMRUN = "ramrun"


class DldTool:
    """DUT UART下载工具封装类"""

    def __init__(
        self,
        com_port: Union[int, str],
        programmer_bin: Optional[str] = None,
        baud_rate: Optional[int] = None,
        verbose: bool = False,
        no_sync: bool = False,
        sync_reply: bool = False,
        no_shutdown: bool = False,
        reboot: bool = False,
        retry: Optional[int] = None,
        no_retry: bool = False,
        pgm_rate: Optional[int] = None,
        sector_size_kib: Optional[int] = None,
        force_uart: bool = False,
        force_usb: bool = False,
    ):
        """
        初始化下载工具

        参数:
            com_port: 串口号(数字或'usb')
            programmer_bin: Programmer二进制文件名或路径(可选，为None时需在调用时自动识别)
            baud_rate: 串口波特率(可选)
            verbose: 是否启用详细日志
            no_sync: 跳过首次同步
            sync_reply: 直接发送同步回复
            no_shutdown: 完成后不关机
            reboot: 完成后重启
            retry: 失败重试次数
            no_retry: 不重试
            pgm_rate: Programmer UART波特率
            sector_size_kib: 扇区大小(KiB)
            force_uart: 强制UART模式
            force_usb: 强制USB模式
        """
        self.com_port = str(com_port)
        self.programmer_bin = self._resolve_bin_path(programmer_bin) if programmer_bin else None
        self.baud_rate = baud_rate
        self.verbose = verbose
        self.no_sync = no_sync
        self.sync_reply = sync_reply
        self.no_shutdown = no_shutdown
        self.reboot = reboot
        self.retry = retry
        self.no_retry = no_retry
        self.pgm_rate = pgm_rate
        self.sector_size_kib = sector_size_kib
        self.force_uart = force_uart
        self.force_usb = force_usb

    @classmethod
    def from_bin(
        cls,
        com_port: Union[int, str],
        bin_file: str,
        **kwargs,
    ) -> "DldTool":
        """
        根据待下载BIN文件自动识别programmer并创建DldTool实例

        参数:
            com_port: 串口号
            bin_file: 待下载BIN文件(用于自动检测programmer)
            **kwargs: 其他DldTool构造参数
        """
        resolved = cls._resolve_bin_path(bin_file)
        programmer = auto_detect_programmer(resolved)
        if programmer is None:
            raise FileNotFoundError(
                f"无法从BIN文件 '{bin_file}' 自动识别对应的programmer"
            )
        return cls(com_port=com_port, programmer_bin=str(programmer), **kwargs)

    def _get_programmer(self, flash_file: Optional[str] = None) -> Path:
        """
        获取programmer路径，支持自动识别

        优先使用已配置的programmer_bin，
        若未配置则尝试从flash_file自动识别
        """
        if self.programmer_bin is not None:
            return self.programmer_bin
        if flash_file is not None:
            resolved = self._resolve_bin_path(flash_file)
            programmer = auto_detect_programmer(resolved)
            if programmer is not None:
                return programmer
        raise ValueError(
            "未指定programmer_bin，且无法从待下载文件自动识别对应的programmer"
        )

    @staticmethod
    def _resolve_bin_path(bin_file: str) -> Path:
        p = Path(bin_file)
        if p.is_absolute() and p.exists():
            return p
        candidate = TOOLS_DIR / bin_file
        if candidate.exists():
            return candidate
        return p

    def _build_common_options(self) -> list[str]:
        opts: list[str] = []
        if self.baud_rate is not None:
            opts += ["-b", str(self.baud_rate)]
        if self.com_port.lower() == "usb":
            opts.append("usb")
        else:
            opts.append(self.com_port)
        if self.verbose:
            opts.append("-v")
        if self.no_sync:
            opts.append("--no-sync")
        if self.sync_reply:
            opts.append("--sync-reply")
        if self.no_shutdown:
            opts.append("--no-shutdown")
        if self.reboot:
            opts.append("--reboot")
        if self.pgm_rate is not None:
            opts += ["--pgm-rate", str(self.pgm_rate)]
        if self.sector_size_kib is not None:
            opts += ["--sector-size-kib", str(self.sector_size_kib)]
        if self.force_uart:
            opts.append("--force-uart")
        if self.force_usb:
            opts.append("--force-usb")
        if self.retry is not None:
            opts += ["--retry", str(self.retry)]
        if self.no_retry:
            opts.append("--no-retry")
        return opts

    _TERMINAL_STATES = frozenset({
        DownloadState.SUCCEEDED,
        DownloadState.FAILED,
        DownloadState.TIMEOUT,
        DownloadState.CANCELLED,
    })

    @staticmethod
    def _parse_state(line: str) -> Optional[DownloadState]:
        if "PROGRAMMING SUCCEEDED" in line:
            return DownloadState.SUCCEEDED
        if "PROGRAMMING FAILED" in line:
            return DownloadState.FAILED
        if "Total processing time" in line:
            return DownloadState.SUCCEEDED
        if "Wait for SYNC started" in line:
            return DownloadState.WAITING_SYNC
        if "[SYNC]: Started" in line:
            return DownloadState.SYNCING
        if "[SYNC]: Confirmed" in line:
            return DownloadState.PROGRAMMING
        return None

    def _run(
        self,
        args: list[str],
        timeout: Optional[float] = None,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        cmd = [str(DLDTOOL_EXE)] + args
        cmd_str = " ".join(cmd)
        logger.info("执行下载命令: %s", cmd_str)

        result = DownloadResult(state=DownloadState.PREPARING)
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False

        def _set_state(new_state: DownloadState):
            if result.state == new_state:
                return
            if result.state in self._TERMINAL_STATES:
                return
            old = result.state
            result.state = new_state
            logger.info("下载状态: %s -> %s", old.value, new_state.value)
            if on_state_change:
                try:
                    on_state_change(new_state)
                except Exception as e:
                    logger.warning("状态回调异常: %s", e)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(TOOLS_DIR),
            )
            self._process = proc

            timer: Optional[threading.Timer] = None
            if timeout is not None:
                def _on_timeout():
                    logger.error("下载命令超时 (%.1fs)", timeout)
                    _set_state(DownloadState.TIMEOUT)
                    proc.kill()
                timer = threading.Timer(timeout, _on_timeout)
                timer.start()

            for raw_line in proc.stdout:
                line = raw_line.rstrip("\n\r")
                if not line:
                    continue
                result.output_lines.append(line)
                logger.debug("[dldtool] %s", line)

                new_state = self._parse_state(line)
                if new_state is not None:
                    _set_state(new_state)

            proc.wait()

            if timer is not None:
                timer.cancel()

            result.returncode = proc.returncode

            if self._cancelled:
                _set_state(DownloadState.CANCELLED)
                result.error_message = "下载已取消"
            elif result.state == DownloadState.TIMEOUT:
                result.error_message = f"下载超时 ({timeout}s)"
            elif result.state == DownloadState.SUCCEEDED:
                result.success = True
            elif proc.returncode != 0:
                _set_state(DownloadState.FAILED)
                result.error_message = f"下载失败, 返回码: {proc.returncode}"
            else:
                if result.state not in (DownloadState.FAILED,):
                    _set_state(DownloadState.SUCCEEDED)
                    result.success = True

        except Exception as e:
            logger.error("下载命令执行异常: %s", e)
            _set_state(DownloadState.FAILED)
            result.error_message = str(e)
        finally:
            self._process = None

        if result.success:
            logger.info("下载完成: %s", result.state.value)
        else:
            logger.error("下载结束: %s - %s", result.state.value, result.error_message)

        return result

    def cancel(self):
        self._cancelled = True
        proc = getattr(self, "_process", None)
        if proc is not None and proc.poll() is None:
            logger.info("正在取消下载...")
            proc.kill()

    def download(
        self,
        mode: DownloadMode = DownloadMode.FLASH,
        flash_files: Optional[list[str]] = None,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        执行下载操作

        参数:
            mode: 下载模式 (FLASH / RAMRUN)
            flash_files: Flash模式下需要烧录的文件列表
            timeout: 超时时间(秒)
            on_state_change: 状态变更回调

        返回:
            DownloadResult
        """
        args = self._build_common_options()

        if mode == DownloadMode.RAMRUN:
            programmer = self._get_programmer()
            args.append("--ramrun")
            args.append(str(programmer))
        elif mode == DownloadMode.FLASH:
            if not flash_files:
                raise ValueError("FLASH模式必须提供至少一个待烧录文件")
            programmer = self._get_programmer(flash_file=flash_files[0])
            args.append(str(programmer))
            for f in flash_files:
                args.append(str(self._resolve_bin_path(f)))
        else:
            raise ValueError(f"不支持的下载模式: {mode}")

        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def flash(
        self,
        flash_files: Union[str, list[str]],
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        Flash烧录

        参数:
            flash_files: 待烧录文件(单个文件名或文件名列表)
            timeout: 超时时间(秒)
            on_state_change: 状态变更回调
        """
        if isinstance(flash_files, str):
            flash_files = [flash_files]
        return self.download(
            mode=DownloadMode.FLASH, flash_files=flash_files,
            timeout=timeout, on_state_change=on_state_change,
        )

    def ramrun(
        self,
        timeout: Optional[float] = 60,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        Ramrun Programmer

        参数:
            timeout: 超时时间(秒)
            on_state_change: 状态变更回调
        """
        return self.download(
            mode=DownloadMode.RAMRUN, timeout=timeout,
            on_state_change=on_state_change,
        )

    def erase_sector(
        self,
        address: str,
        length: Optional[str] = None,
        timeout: Optional[float] = 60,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        擦除扇区

        参数:
            address: 扇区地址 (如 "0x0")
            length: 擦除长度 (可选)
            timeout: 超时时间(秒)
            on_state_change: 状态变更回调
        """
        erase_arg = address if length is None else f"{address}/{length}"
        args = self._build_common_options()
        args += ["-e", erase_arg, str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def erase_chip(
        self,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """擦除整片Flash"""
        args = self._build_common_options()
        args += ["--erase-chip", str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def erase_chip_by_index(
        self,
        index: int,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        按索引擦除指定Flash芯片

        参数:
            index: Flash芯片索引 (-1为boot芯片, -2为所有芯片)
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args += ["--erase-chip-index", str(index), str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def efuse_read(
        self,
        page: int,
        timeout: Optional[float] = 30,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        读取eFuse

        参数:
            page: eFuse页号
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args += ["--efuse-read", str(page), str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def efuse_write(
        self,
        page: int,
        value: str,
        timeout: Optional[float] = 30,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        写入eFuse

        参数:
            page: eFuse页号
            value: 写入值
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args += ["--efuse-write", f"{page}/{value}", str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def write_memory_before_run(
        self, address: str, value: str
    ):
        """设置运行Programmer前写入的内存值(在后续download调用中生效需自行扩展)"""
        logger.info("w4 设置: address=%s, value=%s", address, value)

    def custom_command(
        self,
        reply_len: int,
        msg_type: int,
        msg_data: Optional[list[int]] = None,
        timeout: Optional[float] = 30,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        发送自定义命令

        参数:
            reply_len: 期望的回复数据长度(1字节)
            msg_type: 消息类型(1字节)
            msg_data: 消息数据内容(每个1字节)
            on_state_change: 状态变更回调
        """
        parts = [str(reply_len), str(msg_type)]
        if msg_data:
            parts.extend(str(d) for d in msg_data)
        cust_arg = "/".join(parts)
        args = self._build_common_options()
        args += ["--cust-cmd", cust_arg, str(self._get_programmer())]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def flash_with_address(
        self,
        flash_file: str,
        address: str,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        烧录Flash文件到指定地址

        参数:
            flash_file: 待烧录文件
            address: 烧录地址
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args.append(str(self._get_programmer(flash_file=flash_file)))
        args += ["--addr", address, str(self._resolve_bin_path(flash_file))]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def bulk_write(
        self,
        mem_file: str,
        address: Optional[str] = None,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        批量写入内存

        参数:
            mem_file: 内存文件
            address: 写入地址(可选)
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args.append(str(self._get_programmer()))
        if address:
            args += ["--addr", address]
        args += ["--bulk-write", str(self._resolve_bin_path(mem_file))]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)

    def direct_write(
        self,
        mem_file: str,
        address: Optional[str] = None,
        timeout: Optional[float] = 120,
        on_state_change: Optional[Callable[[DownloadState], None]] = None,
    ) -> DownloadResult:
        """
        直接写入内存

        参数:
            mem_file: 内存文件
            address: 写入地址(可选)
            on_state_change: 状态变更回调
        """
        args = self._build_common_options()
        args.append(str(self._get_programmer()))
        if address:
            args += ["--addr", address]
        args += ["--direct-write", str(self._resolve_bin_path(mem_file))]
        return self._run(args, timeout=timeout, on_state_change=on_state_change)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    )

    logger.info("DldTool 下载工具示例")
    logger.info("=" * 50)

    def on_state(state: DownloadState):
        if state == DownloadState.WAITING_SYNC:
            logger.info(">>> 请重启芯片以开始握手 <<<")

    logger.info("--- 自动识别Programmer ---")
    test_bin = "noapp_test_1307ph_cur_tst.bin"
    chip = detect_chip_from_bin(TOOLS_DIR / test_bin)
    if chip:
        logger.info("BIN文件 '%s' -> 芯片型号: %s -> programmer%s.bin", test_bin, chip, chip)

    logger.info("")
    logger.info("--- Ramrun示例 (COM20) ---")
    logger.info("  等价命令: dldtool.exe 20 --ramrun programmer1307ph.bin")
    dld = DldTool(com_port=20, programmer_bin="programmer1307ph.bin")
    result = dld.ramrun(timeout=60, on_state_change=on_state)
    logger.info("  结果: success=%s, state=%s", result.success, result.state.value)

    # logger.info("")
    # logger.info("--- Flash烧录示例 (COM20, 自动识别programmer) ---")
    # dld_auto = DldTool(com_port=20)
    # result = dld_auto.flash("noapp_test_1307ph_cur_tst.bin", timeout=120, on_state_change=on_state)
    # logger.info("  结果: success=%s, state=%s", result.success, result.state.value)
