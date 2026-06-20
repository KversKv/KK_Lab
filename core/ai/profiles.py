"""AI Profile：页面键 -> 模型参数 + system_prompt。

页面键直接复用 MainWindow.current_instrument_ui（见 _get_current_help_key 验证）。

⚠️ 阶段 1 落地约束（AI_Assist.md §5/§6）：
  - 当前网关仅暴露真实模型 glm-5.1-fp8（默认）与 deepseekv4flash，无功能别名路由；
    因此各 Profile 的 model 一律先映射到实际可用模型，功能差异靠 system_prompt/temperature 体现；
  - glm-5.1-fp8 为推理模型，reasoning 先消耗 token，max_tokens 必须 ≥ 1024，否则 content 可能为空。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from ui.resource_path import get_resource_base, get_user_data_dir
from log_config import get_logger

logger = get_logger(__name__)

_PROJECT_PROMPT_REL = ("resources", "ai", "project_prompt.md")
_USER_PROMPT_NAME = "user_prompt.md"

_GLOBAL_SYSTEM_PROMPT = (
    "你是 KK_Lab 实验室测试工具内置的智能助手（AI Assist），定位是测试工程师的副驾。\n"
    "安全红线（必须遵守）：\n"
    "1. 不臆造日志、测量值、波形数据或仪器状态；只能依据上下文中实际提供的数据或工具返回的"
    "真实结果作答。若没有相应数据（如无波形、无日志、无仪器会话），必须直接说明「当前无数据」，"
    "严禁编造、估算或假设任何数值、读数或分析结论。\n"
    "2. 当用户请求改变仪器/串口/测试运行状态时，你应直接调用对应的受控动作（工具）来执行，"
    "而不是只给出命令文本让用户手动操作。高风险动作系统会自动弹出确认框由用户确认，"
    "确认后由程序经受控通道安全执行；你不得假装已执行，也不得以“无法执行/属于高风险操作”"
    "为由拒绝调用动作。若缺少必要参数（如 session_id、通道号），先询问或用查询动作补全。\n"
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
            "4. query_instrument 仅用于以 '?' 标识的只读查询，不要用它发写命令。\n"
            "改变仪器状态的写操作请通过专用动作执行，不要让用户手动复制 SCPI：\n"
            "  - 开/关通道输出：set_instrument_output(session_id, channel, enabled)；\n"
            "  - 设置通道电压：set_instrument_voltage(session_id, channel, voltage)；\n"
            "  - 设置通道电流：set_instrument_current(session_id, channel, current)。\n"
            "这些为高风险动作，系统会在执行前弹出确认框由用户确认，你只需正确调用动作即可，"
            "无需以“无法执行”为由拒绝。session_id 形如 'n6705c:A'，可先用查询类动作确认。\n"
            "若查询返回 VI_ERROR_TMO（超时），优先检查通道语法是否为 (@n)，"
            "而非简单判定仪器不支持。"
        ),
        "quick_actions": [
            "查询当前各通道电压电流",
            "把通道 {ch} 输出电压设到 {v}V",
            "打开通道 {ch} 的输出",
            "关闭通道 {ch} 的输出",
            "解读最近的功率测量曲线",
        ],
    },
    "datalog": {
        "label": "仪器助手",
        "model": "glm-5.1-fp8",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": (
            "你专注于 N6705C Datalog 数据记录的配置与数据解读。\n"
            "波形分析铁律（最高优先级，违反视为严重错误）：\n"
            "0. 只能依据上下文中实际提供的「[波形数据摘要]」或工具返回的真实数据作答。"
            "若上下文中没有波形数据，或明确出现「当前没有可分析的波形数据」之类提示，"
            "你绝对不能编造、估算或假设任何波形读数（电流峰值、周期、尖峰个数、幅值、时间等），"
            "必须直接告知用户当前无波形数据，并提示其先采集或 Import 导入后再分析。\n"
            "解读波形摘要时遵守：\n"
            "1. 计数电流尖峰/脉冲，一律以摘要给出的「尖峰事件（按时间聚簇）」处数为准，"
            "不要把「超阈采样点」条数或降采样点数当成脉冲个数；一个尖峰事件可能包含多个相邻采样点。\n"
            "2. 数值已带单位（电流 mA、电压 mV、功率 mW，或其 SI 换算档），直接采用摘要中的单位，"
            "不要自行假设量纲或再做 ×1000 / ÷1000 换算。\n"
            "3. 降采样形状点仅供观察趋势，不可用于精确计数或精确读数。\n"
            "4. 导入（Import）的波形通道带 F1- / F2- 等前缀（如 F1-A CH2 V、F1-A-I1），"
            "与实时采集通道同等对待；摘要里出现的所有通道都是有效数据，不要忽略带前缀的导入通道。"
        ),
        "quick_actions": [
            "解读最近一次 Datalog 数据趋势",
            "统计电流尖峰事件的位置与峰值",
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


def get_project_prompt() -> str:
    """读取项目层 prompt（resources/ai/project_prompt.md，随包只读）。

    缺失或读取失败回退空串，不影响拼装。
    """
    path = os.path.join(get_resource_base(), *_PROJECT_PROMPT_REL)
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        logger.error("读取项目层 prompt 失败: %s", path, exc_info=True)
        return ""


def get_user_prompt() -> str:
    """读取用户层 prompt（user_data/ai/user_prompt.md，本机可改）。

    缺失或读取失败回退空串，不影响拼装。
    """
    path = os.path.join(get_user_data_dir("ai"), _USER_PROMPT_NAME)
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        logger.error("读取用户层 prompt 失败: %s", path, exc_info=True)
        return ""


def get_profile(page_key: str | None) -> dict[str, Any]:
    """按页面键取 Profile；未知页面回退 _default。"""
    if page_key and page_key in AI_PROFILES:
        return AI_PROFILES[page_key]
    return AI_PROFILES["_default"]


def get_quick_actions(page_key: str | None) -> list[str]:
    """按页面键取快捷指令文案列表（5.4 快捷指令动态化）。

    文案可含 `{占位符}`（如 `把通道 {ch} 设到 {v}V`），UI 侧对带占位符的项
    弹轻量输入后再发送（见 quick_action_placeholders / fill_quick_action）。
    """
    profile = get_profile(page_key)
    actions = [str(a) for a in (profile.get("quick_actions") or []) if str(a).strip()]
    for extra in _local_quick_actions(page_key):
        if extra not in actions:
            actions.append(extra)
    return actions


_QUICK_ACTIONS_LOCAL = "quick_actions.local.json"


def _local_quick_actions(page_key: str | None) -> list[str]:
    """读取本机沉淀的快捷指令（user_data/ai/quick_actions.local.json）。"""
    path = os.path.join(get_user_data_dir("ai"), _QUICK_ACTIONS_LOCAL)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        logger.error("读取本机快捷指令失败: %s", path, exc_info=True)
        return []
    groups = data.get("quick_actions") or {}
    if not isinstance(groups, dict):
        return []
    key = page_key if (page_key and page_key in groups) else "_default"
    return [str(a) for a in (groups.get(key) or []) if str(a).strip()]


_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def quick_action_placeholders(template: str) -> list[str]:
    """解析快捷指令模板中的占位符名（去重保序），无占位符返回空列表。"""
    seen: list[str] = []
    for name in _PLACEHOLDER_RE.findall(template or ""):
        if name not in seen:
            seen.append(name)
    return seen


def fill_quick_action(template: str, values: dict[str, str]) -> str:
    """用 values 填充模板占位符；缺失的占位符原样保留。"""
    def _sub(match: "re.Match[str]") -> str:
        key = match.group(1)
        val = values.get(key)
        return str(val) if val not in (None, "") else match.group(0)

    return _PLACEHOLDER_RE.sub(_sub, template or "")
