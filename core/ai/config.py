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
    _runtime_api_key: str = field(default="", repr=False, compare=False)

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
            }
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            logger.error("写入 AI 配置失败: %s", path, exc_info=True)
            return False
