"""Audio Precision SSH 会话与远程脚本构造，仅依赖标准库。"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import random
import shlex
import socket
import subprocess
import tempfile
import time
import uuid

from log_config import get_logger
from resource_path import get_resource_base
from .psrr_analysis import AudioPrecisionPSRRConfig

logger = get_logger(__name__)

_PERSISTENT_PYTHON_BOOTSTRAP = (
    "import base64,sys;"
    "exec(compile(base64.b64decode(sys.stdin.readline()),'<kk_lab_psrr_guest>','exec'))"
)
_EVENT_PREFIX = "KK_LAB_PSRR_EVENT:"


def ssh_command(
    config: AudioPrecisionPSRRConfig, *, persistent: bool = False
) -> list[str]:
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    if config.ssh_profile:
        target = config.ssh_profile
    else:
        if not config.ssh_host.strip():
            raise RuntimeError("请填写 Guest IP 或 SSH Profile")
        command.extend(("-p", str(config.ssh_port)))
        target = f"{config.ssh_user}@{config.ssh_host}"
    remote_command = (
        f'{config.ssh_python} -u -c "{_PERSISTENT_PYTHON_BOOTSTRAP}"'
        if persistent else f"{config.ssh_python} -u -"
    )
    command.extend((target, remote_command))
    return command


def remote_config(config: AudioPrecisionPSRRConfig) -> dict:
    return {
        "project_path": config.project_path,
        "signal_path": config.signal_path,
        "measurement": config.measurement,
        "vin_input_channel": config.vin_input_channel,
        "vout_input_channel": config.vout_input_channel,
        "output_channel": config.output_channel,
        "amplitude_vrms": config.amplitude_vrms,
        "offset_v": config.offset_v,
        "bandwidth_hz": config.bandwidth_hz,
        "fft_length": config.fft_length,
        "fft_window": config.fft_window,
        "fft_averages": config.fft_averages,
        "frequencies_hz": list(config.frequencies_hz),
    }


def build_remote_script(
    config: AudioPrecisionPSRRConfig | None = None,
    *,
    persistent: bool = False,
) -> str:
    project_root = Path(get_resource_base())
    parts = [
        project_root / "core" / "pmu_test" / "psrr" / "psrr_analysis.py",
        project_root / "instruments" / "audioPrecision" / "apx500_driver.py",
        project_root / "instruments" / "audioPrecision" / "apx_psrr_guest.py",
    ]
    source = "\n\n".join(path.read_text(encoding="utf-8") for path in parts)
    if persistent:
        return source + "\n\nrun_psrr_guest_session(APxConnection)\n"
    if config is None:
        raise ValueError("One-shot remote script requires a PSRR config")
    encoded = base64.b64encode(
        json.dumps(remote_config(config)).encode("utf-8")
    ).decode("ascii")
    return source + f"\n\nrun_psrr_guest(APxConnection, {encoded!r})\n"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _create_local_listener() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    return listener


class AudioPrecisionSSHSession:
    """在 Guest 交互桌面运行 APx，并通过 SSH 端口转发保持会话。"""

    def __init__(self, config: AudioPrecisionPSRRConfig):
        self.config = config
        self._process: subprocess.Popen | None = None
        self._tunnel_output = None
        self._reader = None
        self._writer = None
        self._socket: socket.socket | None = None
        self._listener: socket.socket | None = None
        self._connected = False
        self._task_name: str | None = None
        self._remote_script: str | None = None
        self._remote_log: str | None = None

    @property
    def connected(self) -> bool:
        return bool(
            self._connected
            and self._process is not None
            and self._process.poll() is None
        )

    def connect(self, on_event) -> None:
        if self.connected:
            return
        try:
            self._open_transport()
            while True:
                event = self._read_event()
                on_event(event)
                event_type = event.get("type")
                if event_type == "connected":
                    self._connected = True
                    return
                if event_type == "error":
                    raise RuntimeError(event.get("message", "APx connection failed"))
        except Exception as exc:
            diagnostics = self._remote_diagnostics()
            self.terminate()
            if diagnostics and diagnostics not in str(exc):
                raise RuntimeError(f"{exc}\n{diagnostics}") from exc
            raise

    def run_sweep(self, config: AudioPrecisionPSRRConfig, on_event) -> None:
        if not self.connected:
            raise RuntimeError("Audio Precision SSH session is not connected")
        self._send_json({"command": "sweep", "config": remote_config(config)})
        while True:
            event = self._read_event()
            on_event(event)
            event_type = event.get("type")
            if event_type == "complete":
                return
            if event_type == "error":
                raise RuntimeError(event.get("message", "APx sweep failed"))

    def set_output(
        self, config: AudioPrecisionPSRRConfig, enabled: bool, on_event
    ) -> None:
        if not self.connected:
            raise RuntimeError("Audio Precision SSH session is not connected")
        self._send_json({
            "command": "output",
            "config": remote_config(config),
            "enabled": bool(enabled),
        })
        while True:
            event = self._read_event()
            on_event(event)
            event_type = event.get("type")
            if event_type == "output_complete":
                return
            if event_type == "error":
                raise RuntimeError(event.get("message", "APx output operation failed"))

    def get_output_state(self, on_event) -> bool:
        if not self.connected:
            raise RuntimeError("Audio Precision SSH session is not connected")
        self._send_json({"command": "output_state"})
        while True:
            event = self._read_event()
            on_event(event)
            event_type = event.get("type")
            if event_type == "output_state":
                return bool(event.get("enabled", False))
            if event_type == "error":
                raise RuntimeError(event.get("message", "APx output state query failed"))

    def disconnect(self) -> None:
        if self._process is None:
            return
        try:
            if self._connected:
                self._send_json({"command": "disconnect"})
                if self._socket is not None:
                    self._socket.settimeout(10)
                while True:
                    event = self._read_event()
                    if event.get("type") == "disconnected":
                        break
        except (OSError, RuntimeError) as exc:
            logger.warning("Audio Precision 正常断开失败: %s", exc)
        finally:
            self.terminate()

    def terminate(self) -> None:
        self._connected = False
        task_name = self._task_name
        self._task_name = None
        if task_name:
            self._cleanup_remote_task(task_name)
        for stream in (self._reader, self._writer):
            if stream is not None and not stream.closed:
                try:
                    stream.close()
                except OSError:
                    logger.debug("关闭 Audio Precision  socket 流失败", exc_info=True)
        self._reader = None
        self._writer = None
        for sock in (self._socket, self._listener):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self._socket = None
        self._listener = None
        process = self._process
        self._process = None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    try:
                        stream.close()
                    except OSError:
                        logger.debug("关闭 Audio Precision SSH 管道失败", exc_info=True)
        if self._tunnel_output is not None:
            self._tunnel_output.close()
            self._tunnel_output = None

    def _open_transport(self) -> None:
        token = uuid.uuid4().hex[:12]
        remote_dir = r"C:\Windows\Temp\KK_Lab"
        self._task_name = f"KKLabAPxPSRR_{token}"
        self._remote_script = remote_dir + rf"\apx_psrr_{token}.py"
        self._remote_log = remote_dir + rf"\apx_psrr_{token}.log"
        remote_port = random.SystemRandom().randint(40000, 60000)
        self._listener = _create_local_listener()
        local_port = int(self._listener.getsockname()[1])
        source = self._build_interactive_script(remote_port)
        self._upload_remote_script(source)
        self._start_tunnel(local_port, remote_port)
        self._start_interactive_task()
        self._accept_socket()

    def _build_interactive_script(self, remote_port: int) -> str:
        source = build_remote_script(persistent=True)
        suffix = "\n\nrun_psrr_guest_session(APxConnection)\n"
        if not source.endswith(suffix):
            raise RuntimeError("Unexpected APx Guest script entry point")
        wrapper = f'''
import socket as _kk_socket
import traceback as _kk_traceback

_kk_connection = None
_kk_deadline = time.time() + 45
while time.time() < _kk_deadline:
    try:
        _kk_connection = _kk_socket.create_connection(("127.0.0.1", {remote_port}), timeout=1)
        break
    except OSError:
        time.sleep(0.1)
if _kk_connection is None:
    with open({self._remote_log!r}, "a", encoding="utf-8") as _kk_log:
        _kk_log.write("Reverse SSH tunnel connection timed out\\n")
    raise RuntimeError("Reverse SSH tunnel connection timed out")
_kk_connection.settimeout(None)
_kk_reader = _kk_connection.makefile("r", encoding="utf-8", newline="\\n")
_kk_writer = _kk_connection.makefile("w", encoding="utf-8", newline="\\n")
sys.stdin = _kk_reader
sys.stdout = _kk_writer
try:
    run_psrr_guest_session(APxConnection)
except Exception:
    with open({self._remote_log!r}, "a", encoding="utf-8") as _kk_log:
        _kk_log.write(_kk_traceback.format_exc())
    raise
finally:
    try:
        _kk_writer.flush()
    finally:
        _kk_writer.close()
        _kk_reader.close()
        _kk_connection.close()
'''
        return source[:-len(suffix)] + wrapper

    def _upload_remote_script(self, source: str) -> None:
        receiver = (
            "import base64,pathlib,sys;"
            f"p=pathlib.Path({self._remote_script!r});"
            "p.parent.mkdir(parents=True,exist_ok=True);"
            "p.write_bytes(base64.b64decode(sys.stdin.read()))"
        )
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        result = self._run_remote(
            f'{self.config.ssh_python} -u -c "{receiver}"', encoded
        )
        if result.returncode:
            raise RuntimeError(f"APx Guest script upload failed: {result.stdout}")

    def _start_interactive_task(self) -> None:
        parts = shlex.split(self.config.ssh_python)
        if not parts:
            raise RuntimeError("Guest Python Command is empty")
        executable = parts[0]
        if "\\" in executable or ":" in executable:
            execute = _ps_quote(executable)
        else:
            execute = f"(Get-Command {_ps_quote(executable)}).Source"
        arguments = subprocess.list2cmdline([*parts[1:], "-u", self._remote_script])
        command = (
            f"$action=New-ScheduledTaskAction -Execute {execute} "
            f"-Argument {_ps_quote(arguments)}; "
            "$principal=New-ScheduledTaskPrincipal "
            "-UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) "
            "-LogonType Interactive -RunLevel Highest; "
            f"Register-ScheduledTask -TaskName {_ps_quote(self._task_name)} "
            "-Action $action -Principal $principal -Force | Out-Null; "
            f"Start-ScheduledTask -TaskName {_ps_quote(self._task_name)}"
        )
        result = self._run_remote(command)
        if result.returncode:
            raise RuntimeError(f"Interactive APx task failed to start: {result.stdout}")

    def _start_tunnel(self, local_port: int, remote_port: int) -> None:
        base = ssh_command(self.config)
        command = base[:-2] + [
            "-N", "-R", f"127.0.0.1:{remote_port}:127.0.0.1:{local_port}", base[-2]
        ]
        self._tunnel_output = tempfile.TemporaryFile(
            mode="w+t", encoding="utf-8", errors="replace"
        )
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=self._tunnel_output,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _accept_socket(self) -> None:
        deadline = time.monotonic() + 45
        self._listener.settimeout(1)
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"SSH tunnel exited: {self._tunnel_status()}")
            try:
                self._socket, _ = self._listener.accept()
                self._socket.settimeout(None)
                self._reader = self._socket.makefile("r", encoding="utf-8", newline="\n")
                self._writer = self._socket.makefile("w", encoding="utf-8", newline="\n")
                self._listener.close()
                self._listener = None
                return
            except socket.timeout:
                continue
        raise RuntimeError(
            "Interactive APx session did not start. "
            + self._remote_diagnostics()
        )

    def _tunnel_status(self) -> str:
        if self._tunnel_output is None:
            return ""
        try:
            self._tunnel_output.seek(0)
            return self._tunnel_output.read().strip()
        except OSError:
            return ""

    def _remote_diagnostics(self) -> str:
        if not self._task_name:
            return ""
        command = (
            f"Get-ScheduledTaskInfo -TaskName {_ps_quote(self._task_name)} "
            "-ErrorAction SilentlyContinue | Format-List LastTaskResult,LastRunTime; "
            f"Get-Content -LiteralPath {_ps_quote(self._remote_log)} -Tail 20 "
            "-ErrorAction SilentlyContinue"
        )
        try:
            result = self._run_remote(command)
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    def _cleanup_remote_task(self, task_name: str) -> None:
        paths = [self._remote_script, self._remote_log]
        remove_command = "; ".join(
            f"Remove-Item -LiteralPath {_ps_quote(path)} -Force -ErrorAction SilentlyContinue"
            for path in paths if path
        )
        command = (
            f"Stop-ScheduledTask -TaskName {_ps_quote(task_name)} -ErrorAction SilentlyContinue; "
            f"Unregister-ScheduledTask -TaskName {_ps_quote(task_name)} "
            "-Confirm:$false -ErrorAction SilentlyContinue; "
            + remove_command
        )
        try:
            self._run_remote(command)
        except (OSError, subprocess.SubprocessError):
            logger.warning("Audio Precision 交互任务清理失败", exc_info=True)
        self._remote_script = None
        self._remote_log = None

    def _run_remote(self, remote_command: str, input_text: str | None = None):
        command = ssh_command(self.config)
        command[-1] = remote_command
        return subprocess.run(
            command,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=30,
            check=False,
        )

    def _send_script(self, script: str) -> None:
        if self._writer is None:
            raise RuntimeError("APx session input is unavailable")
        encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
        self._writer.write(encoded + "\n")
        self._writer.flush()

    def _send_json(self, payload: dict) -> None:
        if self._writer is None:
            raise RuntimeError("APx session input is unavailable")
        encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        self._writer.write(encoded + "\n")
        self._writer.flush()

    def _read_event(self) -> dict:
        if self._reader is None:
            raise RuntimeError("APx session output is unavailable")
        while True:
            line = self._reader.readline()
            if not line:
                self._connected = False
                details = self._tunnel_status()
                suffix = f"\n{details}" if details else ""
                raise RuntimeError("Interactive APx session ended" + suffix)
            line = line.strip()
            if not line:
                continue
            if not line.startswith(_EVENT_PREFIX):
                return {"type": "log", "message": line}
            encoded = line.split(":", 1)[1]
            return json.loads(base64.b64decode(encoded).decode("utf-8"))
