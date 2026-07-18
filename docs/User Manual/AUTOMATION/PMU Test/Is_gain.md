# Is_gain

测量 BES 芯片 **电流源（Current Source）增益**：通过 I2C 设置不同电流源档位，N6705C 测量实际输出电流，示波器辅助捕获瞬态响应，计算增益精度。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `Is_gain`
- 对应源码：`ui/pages/pmu_test/pmu_isGain_ui.py`（`PMUIsGainUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，测电流通道。
- **Oscilloscope 连接卡片**：`OscilloscopeConnectionMixin`，捕获瞬态波形。
- **Test Config 卡片**：
  - Current Source 列表（多选）
  - Gain Range：增益档位扫描范围
  - Step：步进
  - Load Resistor (Ω)：外接采样电阻
- **CardFrame 卡片式布局**：标题带紫色 accent bar，统一页面 QSS。

### 2. 右侧图表与结果表
- **Iout vs Gain Setting** 曲线（理想 + 实测）。
- **Error (%) vs Gain** 曲线。
- 结果表：档位 / Iout (mA) / Error (%) / PASS/FAIL。

### 3. 底部 — Execution Logs
- 打印每个增益档位的 I2C 写入、N6705C 电流回读、示波器波形捕获事件。

## 典型操作流程

1. 连接 N6705C（电流通道）与示波器（探测电流源输出节点）。
2. 进入本页 → 勾选要测的电流源。
3. 设增益扫描范围与步进。
4. 输入采样电阻值。
5. 点击 `▷ Start`。
6. 线程逐档位：I2C 写入 → 示波器捕获瞬态 → N6705C 读稳态电流 → 计算增益。
7. 测试完成保存 CSV + 图表 + 示波器波形截图。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Gain Setting | — | I2C 配置的电流源增益档位 |
| Iout | mA | N6705C 实测输出电流 |
| Load Resistor | Ω | 外接采样电阻，用于计算理论电流 |
| Error | % | (Iout - I_ideal) / I_ideal × 100% |

## 注意事项

- **示波器触发**：瞬态捕获依赖正确的触发设置，建议先在 Oscilloscope 页面调好触发再回到本页。
- **采样电阻精度**：误差直接影响 I_ideal 计算，建议使用 0.1% 精密电阻。
- **AI 契约**：实现完整的 5 个能力（APPLY_CONFIG / GET_CONFIG / GET_RESULT / START_TEST / STOP_TEST）。
- **AI 高风险动作**：已注册 UIActionSpec，AI 调用 `Start` 前会请求确认。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C / 示波器 / I2C 均走 Mock。
