# Regulation Voltage Test

测量充电器**调压（Regulation Voltage / VREG）**精度：I2C 设置 VREG，N6705C 实测电池引脚电压，计算偏差。

## 页面入口

- 导航栏 → `AUTOMATION` → `Charger Test` → 子菜单 `Regulation Voltage Test`
- 对应源码：`ui/pages/charger_test/regulation_voltage_ui.py`（`RegulationVoltageTestUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：VBUS 通道 + VBATT 通道（实测 VREG）。
- **I2C Config 卡片**：设备地址、速度模式。
- **Test Config 卡片**：
  - VREG Range / Step：电压扫描范围与步进（如 3.8V~4.4V，步进 20mV）
  - Charge Current：充电电流（mA）
  - Settling Time (ms)：每次设置后等待稳定时间

### 2. 右侧图表区
- **Vout vs Vset** 曲线（理想 + 实测）。
- **Error (mV) vs Vset** 曲线。
- QtCharts 鼠标缩放/平移/Marker 交互。

### 3. 底部 — Execution Logs
- 打印每次 I2C 写入、N6705C 回读、误差计算。

## 典型操作流程

1. 连接 N6705C：VBUS 接充电器 VBUS，VBATT 接电池引脚（用 4 线制测量避免线损）。
2. 进入本页 → 配置 I2C 参数。
3. 设 VREG Range 3.8~4.4V，Step 20mV。
4. 设 Charge Current 200mA（小电流避免大线损）。
5. `▷ Start` → 线程扫描每个 VREG 值：I2C 写入 → 等待 Settling → N6705C 回读 → 记录。
6. 测试完成保存 CSV + 图表。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Vset (VREG) | V | I2C 配置的调压值 |
| Vout | V | N6705C 实测电池引脚电压 |
| Error | mV | Vout - Vset |
| Charge Current | mA | 测试期间维持的充电电流 |

## 注意事项

- **4 线制测量**：调压精度通常 ±10mV 级，建议用 4 线制（Kelvin）连接，避免线损引入误差。
- **小电流测试**：大电流会引入线损压降，建议 Charge Current ≤ 200mA。
- **Settling Time**：电压调整后需等待 LDO/BUCK 稳定，建议 ≥ 200ms。
- **AI 契约**：实现 5 个能力。
- **AI 高风险**：`Start` 已注册为高风险动作。
- **Mock 模式**：`DEBUG_MOCK=True` 时全部走 Mock。
- **结果文件**：输出到 `Results/charger_regulation_voltage/<时间戳>/`。
