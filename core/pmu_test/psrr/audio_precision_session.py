"""Audio Precision SSH 会话与远程脚本构造，仅依赖标准库。"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess

from log_config import get_logger
from resource_path import get_resource_base
from .psrr_analysis import AudioPrecisionPSRRConfig

logger = get_logger(__name__)

_PERSISTENT_PYTHON_BOOTSTRAP = (
    "import base64,sys;"
    "exec(compile(base64.b64decode(sys.stdin.readline()),'<kk_lab_psrr_guest>','exec'))"
)


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
        "output_channel": config.output_channel,
        "amplitude_vrms": config.amplitude_vrms,
        "offset_v": config.offset_v,
        "bandwidth_hz": config.bandwidth_hz,
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


class AudioPrecisionSSHSession:
    """保持一个 SSH/APx 进程，并允许多次扫频后主动断开。"""

    def __init__(self, config: AudioPrecisionPSRRConfig):
        self.config = config
        self._process: subprocess.Popen | None = None
        self._connected = False

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
        self._process = subprocess.Popen(
            ssh_command(self.config, persistent=True),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            self._send_script(build_remote_script(persistent=True))
            while True:
                event = self._read_event()
                on_event(event)
                event_type = event.get("type")
                if event_type == "connected":
                    self._connected = True
                    return
                if event_type == "error":
                    raise RuntimeError(event.get("message", "APx connection failed"))
        except Exception:
            self.terminate()
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

    def disconnect(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            if process.poll() is None:
                self._send_json({"command": "disconnect"})
                if process.stdin is not None:
                    process.stdin.close()
                process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("Audio Precision SSH 正常断开失败，转为终止会话", exc_info=True)
        finally:
            self.terminate()

    def terminate(self) -> None:
        self._connected = False
        process = self._process
        self._process = None
        if process is None:
            return
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

    def _send_script(self, script: str) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("SSH process stdin is unavailable")
        encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
        self._process.stdin.write(encoded + "\n")
        self._process.stdin.flush()

    def _send_json(self, payload: dict) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("SSH process stdin is unavailable")
        encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        self._process.stdin.write(encoded + "\n")
        self._process.stdin.flush()

    def _read_event(self) -> dict:
        process = self._process
        if process is None or process.stdout is None:
            raise RuntimeError("SSH process stdout is unavailable")
        while True:
            line = process.stdout.readline()
            if not line:
                self._connected = False
                raise RuntimeError(f"SSH session ended with code {process.poll()}")
            line = line.strip()
            if not line:
                continue
            if not line.startswith("KK_LAB_PSRR_EVENT:"):
                return {"type": "log", "message": line}
            encoded = line.split(":", 1)[1]
            return json.loads(base64.b64decode(encoded).decode("utf-8"))
