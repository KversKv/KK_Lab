"""AI Assist 配置读写。

事实源与优先级（与 AI_Assist.md §14 一致，禁硬编码 Key）：
  环境变量 KK_LAB_AI_BASE_URL / KK_LAB_AI_API_KEY / KK_LAB_AI_MODEL
  > user_data/ai/config.json 的 ai.{...}
  > 内置默认值

config.json 路径：get_user_data_dir("ai")/config.json
  开发态 -> <项目根>/user_data/ai/config.json
  打包后 -> %APPDATA%/KK_Lab/ai/config.json
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from ui.resource_path import get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_ENV_BASE_URL = "KK_LAB_AI_BASE_URL"
_ENV_API_KEY = "KK_LAB_AI_API_KEY"
_ENV_MODEL = "KK_LAB_AI_MODEL"
_ENV_TELEMETRY_ENDPOINT = "KK_LAB_AI_TELEMETRY_ENDPOINT"

_CONFIG_FILENAME = "config.json"

_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "base_url": "",
    "api_key": "",
    "default_model": "deepseekv4flash",
    "model_mode": "fixed",
    "available_models": ["deepseekv4flash", "glm-5.1-fp8"],
    "stream": True,
    "timeout_seconds": 60,
    "max_recent_log_lines": 300,
    "enable_log_masking": True,
    "require_confirm_high_risk_action": True,
    "panel_default_open": False,
    "panel_width": 360,
    "model_context_windows": {
        "glm-5.1-fp8": 131072,
        "deepseekv4flash": 1048576,
    },
    "default_context_window": 131072,
    "reserve_output_tokens": 4096,
    "soft_budget_ratio": 0.5,
    "max_context_block_tokens": 8192,
    "summary_trigger_ratio": 0.7,
    "enable_history_summary": True,
    "summary_model": "deepseekv4flash",
    "curator_ai_assist_enabled": True,
    "curator_draft_model": "deepseekv4flash",
    "telemetry_enabled": True,
    "telemetry_endpoint": "",
    "telemetry_batch_size": 20,
    "telemetry_flush_interval_s": 300,
    "telemetry_client_id": "",
    "trace_enabled": True,
}


def _config_path() -> str:
    return os.path.join(get_user_data_dir("ai"), _CONFIG_FILENAME)


@dataclass
class AISettings:
    """AI Assist 运行时配置（只读快照 + 显式落盘）。"""

    enabled: bool = True
    base_url: str = ""
    api_key: str = ""
    default_model: str = "deepseekv4flash"
    model_mode: str = "fixed"
    available_models: list[str] = field(
        default_factory=lambda: ["deepseekv4flash", "glm-5.1-fp8"]
    )
    stream: bool = True
    timeout_seconds: int = 60
    max_recent_log_lines: int = 300
    enable_log_masking: bool = True
    require_confirm_high_risk_action: bool = True
    panel_default_open: bool = False
    panel_width: int = 360
    model_context_windows: dict[str, int] = field(
        default_factory=lambda: {
            "glm-5.1-fp8": 131072,
            "deepseekv4flash": 1048576,
        }
    )
    default_context_window: int = 131072
    reserve_output_tokens: int = 4096
    soft_budget_ratio: float = 0.5
    max_context_block_tokens: int = 8192
    summary_trigger_ratio: float = 0.7
    enable_history_summary: bool = True
    summary_model: str = "deepseekv4flash"
    curator_ai_assist_enabled: bool = True
    curator_draft_model: str = "deepseekv4flash"
    telemetry_enabled: bool = True
    telemetry_endpoint: str = ""
    telemetry_batch_size: int = 20
    telemetry_flush_interval_s: int = 300
    telemetry_client_id: str = ""
    trace_enabled: bool = True
    _runtime_api_key: str = field(default="", repr=False, compare=False)

    def context_window_for(self, model: str) -> int:
        """按模型取上下文窗口；未知模型回退最小已知窗口（保守不溢出）。"""
        windows = self.model_context_windows or {}
        if model and model in windows:
            try:
                return int(windows[model])
            except (TypeError, ValueError):
                pass
        if windows:
            try:
                return min(int(v) for v in windows.values())
            except (TypeError, ValueError):
                pass
        return int(self.default_context_window)

    @property
    def effective_api_key(self) -> str:
        """运行时实际使用的 Key（env > 临时输入 > 文件）。"""
        env_key = os.environ.get(_ENV_API_KEY, "").strip()
        if env_key:
            return env_key
        if self._runtime_api_key:
            return self._runtime_api_key
        return self.api_key

    @property
    def effective_base_url(self) -> str:
        env_base = os.environ.get(_ENV_BASE_URL, "").strip()
        return (env_base or self.base_url).rstrip("/")

    @property
    def effective_model(self) -> str:
        env_model = os.environ.get(_ENV_MODEL, "").strip()
        return env_model or self.default_model

    @property
    def effective_telemetry_endpoint(self) -> str:
        """遥测上报地址（env > 文件）；为空表示未配置上报，仅本地缓冲。"""
        env_ep = os.environ.get(_ENV_TELEMETRY_ENDPOINT, "").strip()
        return (env_ep or self.telemetry_endpoint).strip()

    def set_runtime_api_key(self, key: str) -> None:
        """设置仅本会话内存生效的临时 Key（不落盘明文）。"""
        self._runtime_api_key = (key or "").strip()

    def is_configured(self) -> bool:
        return bool(self.effective_base_url and self.effective_api_key)

    @classmethod
    def load(cls) -> "AISettings":
        data: dict[str, Any] = dict(_DEFAULTS)
        path = _config_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f) or {}
                section = raw.get("ai", {})
                if isinstance(section, dict):
                    data.update({k: section[k] for k in section if k in _DEFAULTS})
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("读取 AI 配置失败: %s", path, exc_info=True)
        models = data.get("available_models")
        if not isinstance(models, list) or not models:
            data["available_models"] = list(_DEFAULTS["available_models"])
        else:
            data["available_models"] = [str(m) for m in models if str(m).strip()]
        if str(data.get("model_mode")) not in ("auto", "fixed"):
            data["model_mode"] = _DEFAULTS["model_mode"]
        windows = data.get("model_context_windows")
        if not isinstance(windows, dict) or not windows:
            data["model_context_windows"] = dict(_DEFAULTS["model_context_windows"])
        else:
            clean_windows: dict[str, int] = {}
            for key, val in windows.items():
                try:
                    clean_windows[str(key)] = int(val)
                except (TypeError, ValueError):
                    continue
            data["model_context_windows"] = (
                clean_windows or dict(_DEFAULTS["model_context_windows"])
            )
        return cls(**data)

    def save(self) -> bool:
        """把可持久化字段写回 config.json（不写运行时临时 Key）。"""
        path = _config_path()
        payload = {
            "ai": {
                "enabled": self.enabled,
                "base_url": self.base_url,
                "api_key": self.api_key,
                "default_model": self.default_model,
                "model_mode": self.model_mode,
                "available_models": list(self.available_models),
                "stream": self.stream,
                "timeout_seconds": self.timeout_seconds,
                "max_recent_log_lines": self.max_recent_log_lines,
                "enable_log_masking": self.enable_log_masking,
                "require_confirm_high_risk_action": self.require_confirm_high_risk_action,
                "panel_default_open": self.panel_default_open,
                "panel_width": self.panel_width,
                "model_context_windows": dict(self.model_context_windows),
                "default_context_window": self.default_context_window,
                "reserve_output_tokens": self.reserve_output_tokens,
                "soft_budget_ratio": self.soft_budget_ratio,
                "max_context_block_tokens": self.max_context_block_tokens,
                "summary_trigger_ratio": self.summary_trigger_ratio,
                "enable_history_summary": self.enable_history_summary,
                "summary_model": self.summary_model,
                "curator_ai_assist_enabled": self.curator_ai_assist_enabled,
                "curator_draft_model": self.curator_draft_model,
                "telemetry_enabled": self.telemetry_enabled,
                "telemetry_endpoint": self.telemetry_endpoint,
                "telemetry_batch_size": self.telemetry_batch_size,
                "telemetry_flush_interval_s": self.telemetry_flush_interval_s,
                "telemetry_client_id": self.telemetry_client_id,
                "trace_enabled": self.trace_enabled,
            }
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            logger.error("写入 AI 配置失败: %s", path, exc_info=True)
            return False
