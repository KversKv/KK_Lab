# Config Traverse Test

对充电器**配置寄存器**做全遍历验证：枚举每个配置位的所有合法值，检查 DUT 是否正确响应（无异常、状态寄存器无故障位）。

## 页面入口

- 导航栏 → `AUTOMATION` → `Charger Test` → 子菜单 `Config Traverse Test`
- 对应源码：`ui/pages/charger_test/config_traverse_test.py`（`ConfigTraverseTestUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：提供 VBUS / VBATT 电源。
- **I2C Config 卡片**：USB-I2C 设备地址、速度模式。
- **Test Config 卡片**：
  - Register List：要遍历的配置寄存器列表
  - Bit Field Range：每个位域的扫描范围
  - Settling Time (ms)：每次写入后等待稳定时间
  - Stop on Fault：遇故障位是否立即停止

### 2. 右侧结果表
- 列：寄存器 / 位域 / 写入值 / 状态寄存器回读 / 故障位 / 结果（PASS/FAIL）。
- QtCharts 可选展示故障率统计。

### 3. 底部 — Execution Logs
- 打印每次写入与回读、故障位触发事件。

## 典型操作流程

1. 在 N6705C Analyser 页连接 N6705C，VBUS 通道接充电器 VBUS 引脚，VBATT 通道接电池引脚。
2. 进入本页 → 配置 I2C 参数。
3. 选择要遍历的寄存器（如充电电流、输入电流限制、调压寄存器）。
4. 设 Settling Time 100ms，勾选 Stop on Fault。
5. `▷ Start` → 线程枚举每个位域值 → 写入 → 等待 → 读状态寄存器 → 记录。
6. 测试完成保存 CSV。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Register | hex | 配置寄存器地址 |
| Bit Field | — | 位域名称（如 CHG_CONFIG） |
| Settling Time | ms | 写入后等待稳定时间 |
| Stop on Fault | bool | 遇故障位是否立即停止 |

## 注意事项

- **I2C 地址宽度**：充电器寄存器通常是 8 位地址 + 8 位数据，由 `I2CWidthFlag` 控制，不要混用。
- **故障位定义**：见 `status_register_test.py::STATUS_REGISTER_MAP`。
- **AI 契约**：实现 5 个能力，AI 可批量遍历。
- **AI 高风险**：`Start` 已注册为高风险动作，AI 调用前请求确认。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C 与 I2C 走 Mock。
