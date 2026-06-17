"""AI Profile：页面键 -> 模型参数 + system_prompt。

页面键直接复用 MainWindow.current_instrument_ui（见 _get_current_help_key 验证）。

⚠️ 阶段 1 落地约束（AI_Assist.md §5/§6）：
  - 当前网关仅暴露真实模型 glm-5.1-fp8（默认）与 deepseekv4flash，无功能别名路由；
    因此各 Profile 的 model 一律先映射到实际可用模型，功能差异靠 system_prompt/temperature 体现；
  - glm-5.1-fp8 为推理模型，reasoning 先消耗 token，max_tokens 必须 ≥ 1024，否则 content 可能为空。
"""
from __future__ import annotations

from typing import Any

_GLOBAL_SYSTEM_PROMPT = (
    "你是 KK_Lab 实验室测试工具内置的智能助手（AI Assist），定位是测试工程师的副驾。\n"
    "安全红线（必须遵守）：\n"
    "1. 不臆造日志、测量值或仪器状态；不确定时明确说明。\n"
    "2. 你只能在受控范围内提供分析与建议；任何会改变仪器/串口/测试运行状态的动作，"
    "都必须经用户在界面上确认后由程序执行，你不得假装已执行。\n"
    "3. 回答简洁、面向工程实践，使用中文（简体）。\n"
)

AI_PROFILES: dict[str, dict[str, Any]] = {
    "kk_serials": {
        "label": "串口日志助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_prompt": (
            "你专注于 KK_Lab 串口日志分析，聚焦异常、超时、复位、协议错误。"
            "分析时引用具体日志行，禁止臆造日志内容。"
        ),
        "quick_actions": [
            "分析最近串口接收的异常",
            "解释这段串口日志的协议含义",
            "排查串口超时/无响应的可能原因",
        ],
    },
    "power_analyser": {
        "label": "仪器助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": (
            "你专注于 N6705C 电源分析仪的使用与测量解读。\n"
            "通过 query_instrument 发送只读 SCPI 查询时，必须遵守 N6705C 语法：\n"
            "1. 通道一律用 (@n) 形式，禁止用 CHn / CH1 / channel1 等写法；\n"
            "   正确：MEAS:CURR? (@1)；错误：MEAS:CURR? CH1。\n"
            "2. 读通道电流：MEAS:CURR? (@n)；读通道电压：MEAS:VOLT? (@n)。\n"
            "3. 仪器标识：*IDN?；通道输出状态：OUTP? (@n)。\n"
            "4. 只发以 '?' 标识的只读查询，禁止发会改变仪器状态的写命令。\n"
            "若查询返回 VI_ERROR_TMO（超时），优先检查通道语法是否为 (@n)，"
            "而非简单判定仪器不支持。"
        ),
        "quick_actions": [
            "查询当前各通道电压电流",
            "解读最近的功率测量曲线",
            "给出 N6705C 常用 SCPI 查询命令",
        ],
    },
    "datalog": {
        "label": "仪器助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": "你专注于 N6705C Datalog 数据记录的配置与数据解读。",
        "quick_actions": [
            "解读最近一次 Datalog 数据趋势",
            "建议合适的采样率与时长",
        ],
    },
    "oscilloscope": {
        "label": "仪器助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": "你专注于示波器（DSOX4034A / MSO64B）波形测量与触发设置。",
        "quick_actions": [
            "解读当前波形测量结果",
            "建议合适的触发与时基设置",
        ],
    },
    "thermal_chamber": {
        "label": "仪器助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": "你专注于 VT6002 温箱的温度控制与稳定性判断。",
        "quick_actions": [
            "判断当前温度是否已稳定",
            "建议合适的温度梯度与保温时间",
        ],
    },
    "pmu_test": {
        "label": "测试配置助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_prompt": "你专注于 PMU 测试（DCDC 效率/输出电压/IS Gain/OSCP 等）的配置与结果分析。",
        "quick_actions": [
            "生成一份 DCDC 效率测试配置草案",
            "分析最近一次 PMU 测试结果",
            "解释 IS Gain / OSCP 测试要点",
        ],
    },
    "charger_test": {
        "label": "测试配置助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_prompt": "你专注于充电测试（配置遍历/状态寄存器/Iterm/调压等）的配置与结果分析。",
        "quick_actions": [
            "生成一份充电测试配置草案",
            "解读充电状态寄存器含义",
            "分析最近一次充电测试结果",
        ],
    },
    "consumption_test": {
        "label": "测试配置助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_prompt": "你专注于功耗测试的配置与电流功耗数据解读。",
        "quick_actions": [
            "生成一份功耗测试配置草案",
            "解读最近一次功耗电流数据",
        ],
    },
    "custom_test": {
        "label": "脚本助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.0,
        "max_tokens": 4096,
        "system_prompt": (
            "你专注于 Custom Test 测试序列。只能生成符合 core/custom_test 节点 schema 的序列草案，"
            "草案必须经预览与本地校验通过后才能应用，禁止直接运行高风险序列。"
        ),
        "quick_actions": [
            "生成一个简单的测试序列草案",
            "解释可用的节点类型",
            "检查当前序列的潜在问题",
        ],
    },
    "vmin_hunter": {
        "label": "测试配置助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.1,
        "max_tokens": 2048,
        "system_prompt": "你专注于 VminHunter 最低工作电压搜索的配置与结果解读。",
        "quick_actions": [
            "解读最近一次 Vmin 搜索结果",
            "建议合适的搜索步进与范围",
        ],
    },
    "collection": {
        "label": "通用助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": "你是 KK_Lab 的通用智能助手。",
        "quick_actions": [
            "介绍 KK_Lab 的主要功能",
            "分析最近的运行日志",
        ],
    },
    "_default": {
        "label": "通用助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": "你是 KK_Lab 测试工具的智能助手。",
        "quick_actions": [
            "介绍当前页面能做什么",
            "分析最近的运行日志",
        ],
    },
}


def get_global_system_prompt() -> str:
    return _GLOBAL_SYSTEM_PROMPT


def get_profile(page_key: str | None) -> dict[str, Any]:
    """按页面键取 Profile；未知页面回退 _default。"""
    if page_key and page_key in AI_PROFILES:
        return AI_PROFILES[page_key]
    return AI_PROFILES["_default"]


def get_quick_actions(page_key: str | None) -> list[str]:
    """按页面键取快捷指令文案列表（5.4 快捷指令动态化）。"""
    profile = get_profile(page_key)
    actions = profile.get("quick_actions") or []
    return [str(a) for a in actions if str(a).strip()]
