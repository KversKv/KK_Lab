"""AI Assist 阶段 0 网关连通性冒烟测试（New API / OpenAI 兼容）。

用途：在写 core/ai 功能代码前，验证 [AI_AssistPlan.md 阶段 0] 的 0.1~0.4、0.6——
  - 0.1 base_url 完整路径是否可达；
  - 0.2 鉴权头（Authorization: Bearer <key>）是否被接受；
  - 0.3 列出可用 model 名称；
  - 0.4 原生 tools(function calling) 与 stream 是否支持；
  - 0.6 跑通一条最小 /chat/completions 请求并留存样例。

配置读取优先级（与 AI_Assist.md §14 一致，禁硬编码 Key）：
  环境变量 KK_LAB_AI_BASE_URL / KK_LAB_AI_API_KEY / KK_LAB_AI_MODEL
  > user_data/ai/config.json 的 ai.{base_url,api_key,default_model}

运行：
  .\\.venv\\Scripts\\python.exe scripts\\ai_smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed in current interpreter:", sys.executable)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "user_data" / "ai" / "config.json"


def load_config() -> dict:
    cfg = {}
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = (json.load(f) or {}).get("ai", {})
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARN: 读取 {CONFIG_PATH} 失败: {exc}")
    base_url = os.environ.get("KK_LAB_AI_BASE_URL") or cfg.get("base_url", "")
    api_key = os.environ.get("KK_LAB_AI_API_KEY") or cfg.get("api_key", "")
    model = os.environ.get("KK_LAB_AI_MODEL") or cfg.get("default_model", "")
    return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model}


def mask(key: str) -> str:
    if not key:
        return "<空>"
    if len(key) <= 8:
        return key[0] + "***"
    return f"{key[:5]}...{key[-4:]}"


def make_client() -> httpx.Client:
    # trust_env=False：绕过系统代理，确保 localhost 网关直连。
    return httpx.Client(trust_env=False, timeout=30.0)


def probe_models(client: httpx.Client, base_url: str, headers: dict) -> list:
    url = f"{base_url}/models"
    try:
        r = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        print(f"[0.1/0.2] GET {url} 失败: {exc.__class__.__name__}: {exc}")
        return []
    print(f"[0.1/0.2] GET {url} -> {r.status_code}")
    if r.status_code != 200:
        print("  响应:", r.text[:500])
        return []
    try:
        data = r.json().get("data", [])
    except json.JSONDecodeError:
        print("  非 JSON 响应:", r.text[:500])
        return []
    models = [m.get("id", "") for m in data if m.get("id")]
    print(f"[0.3] 可用模型 {len(models)} 个: {', '.join(models[:30])}")
    return models


def probe_chat(client: httpx.Client, base_url: str, headers: dict, model: str) -> bool:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping，请只回复 pong"}],
        "max_tokens": 16,
        "stream": False,
    }
    try:
        r = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        print(f"[0.6] POST {url} 失败: {exc.__class__.__name__}: {exc}")
        return False
    print(f"[0.6] POST {url} (model={model}) -> {r.status_code}")
    if r.status_code != 200:
        print("  响应:", r.text[:800])
        return False
    try:
        body = r.json()
        content = body["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        print(f"  解析失败 ({exc}); 原始: {r.text[:800]}")
        return False
    print("  样例回复:", repr(content)[:300])
    return True


def probe_tools(client: httpx.Client, base_url: str, headers: dict, model: str) -> None:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "现在北京几点？调用工具查询。"}],
        "max_tokens": 64,
        "stream": False,
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "获取指定城市当前时间",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }],
        "tool_choice": "auto",
    }
    try:
        r = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        print(f"[0.4 tools] 请求失败: {exc.__class__.__name__}: {exc}")
        return
    if r.status_code != 200:
        print(f"[0.4 tools] -> {r.status_code}; 不支持或被拒: {r.text[:400]}")
        return
    try:
        msg = r.json()["choices"][0]["message"]
    except (json.JSONDecodeError, KeyError, IndexError):
        print("[0.4 tools] 响应异常:", r.text[:400])
        return
    if msg.get("tool_calls"):
        print("[0.4 tools] 支持原生 tools（返回 tool_calls）")
    else:
        print("[0.4 tools] 未返回 tool_calls，建议第一版走降级 JSON 模式（§9）")


def probe_stream(client: httpx.Client, base_url: str, headers: dict, model: str) -> None:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "数 1 到 3"}],
        "max_tokens": 32,
        "stream": True,
    }
    try:
        chunks = 0
        with client.stream("POST", url, headers=headers, json=payload) as r:
            if r.status_code != 200:
                r.read()
                print(f"[0.4 stream] -> {r.status_code}; 不支持: {r.text[:300]}")
                return
            for line in r.iter_lines():
                if line and line.startswith("data:"):
                    chunks += 1
        if chunks > 0:
            print(f"[0.4 stream] 支持 SSE 流式（收到 {chunks} 个 data 块）")
        else:
            print("[0.4 stream] 200 但无 SSE data 块，按非流式处理")
    except httpx.HTTPError as exc:
        print(f"[0.4 stream] 请求失败: {exc.__class__.__name__}: {exc}")


def main() -> int:
    cfg = load_config()
    print("=" * 60)
    print("AI Assist 阶段 0 网关冒烟测试")
    print(f"  base_url : {cfg['base_url'] or '<空>'}")
    print(f"  api_key  : {mask(cfg['api_key'])}")
    print(f"  model    : {cfg['model'] or '<空>'}")
    print("=" * 60)
    if not cfg["base_url"] or not cfg["api_key"]:
        print("ERROR: base_url 或 api_key 缺失，请配置 user_data/ai/config.json 或环境变量。")
        return 2

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    with make_client() as client:
        models = probe_models(client, cfg["base_url"], headers)
        model = cfg["model"] or (models[0] if models else "")
        if not model:
            print("ERROR: 无可用模型，无法继续 /chat/completions 测试。")
            return 3
        if cfg["model"] and models and cfg["model"] not in models:
            print(f"WARN: 配置的 model '{cfg['model']}' 不在可用列表，改用 '{models[0]}'")
            model = models[0]
        ok = probe_chat(client, cfg["base_url"], headers, model)
        probe_tools(client, cfg["base_url"], headers, model)
        probe_stream(client, cfg["base_url"], headers, model)
    print("=" * 60)
    if ok:
        print("结论：阶段 0 网关连通 OK（0.1~0.4、0.6 已实测）。")
        return 0
    print("结论：/chat/completions 未跑通，请检查网关/模型/Key。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
