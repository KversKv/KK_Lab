# Iterm Test

测量充电器**终止电流（Iterm）**精度：在充电进入恒压阶段后，当电流降到 Iterm 阈值时充电应停止，本测试验证实际停止电流与配置阈值的偏差。

## 页面入口

- 导航栏 → `AUTOMATION` → `Charger Test` → 子菜单 `Iterm Test`
- 对应源码：`ui/pages/charger_test/iterm_test.py`（`ItermTestUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：VBUS 通道 + VBATT 通道（VBATT 用于回读充电电流）。
- **I2C Config 卡片**：设备地址、速度模式。
- **Test Config 卡片**：
  - Iterm Setting：I2C 配置的 Iterm 阈值（mA）
  - Charge Current：初始充电电流（mA）
  - Regulation Voltage：恒压阶段电压（V）
  - Settling Time (s)：进入恒压后等待稳定的时长
  - Sample Period (ms)：电流采样周期

### 2. 右侧图表区
- **充电电流时间曲线**（QtCharts）：从恒流阶段过渡到恒压阶段，直到电流降到 Iterm 以下充电停止。
- 标记实际停止时刻与对应的实际电流值。
- 散点叠加显示每个采样点。

### 3. 底部 — Execution Logs
- 打印 I2C 写入、N6705C 电流回读、状态寄存器变化（CHG_STAT 从充电中→充满）。

## 典型操作流程

1. 连接 N6705C：VBUS 接充电器 VBUS，VBATT 接电池引脚（用作电子负载回读电流）。
2. 进入本页 → 配置 I2C 参数。
3. 设 Iterm Setting 50mA、Charge Current 500mA、Regulation Voltage 4.2V。
4. Settling Time 设 30s（让充电进入恒压阶段）。
5. `▷ Start` → I2C 写入配置 → N6705C 启动充电 → 持续采样电流 → 检测 CHG_STAT 跳变 → 记录实际 Iterm。
6. 测试完成输出报告：实际 Iterm / 设置 Iterm / 偏差 / PASS-FAIL。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Iterm Setting | mA | I2C 配置的终止电流阈值 |
| Charge Current | mA | 初始充电电流（恒流阶段） |
| Regulation Voltage | V | 恒压阶段电压 |
| Actual Iterm | mA | 实测的充电停止电流 |

## 注意事项

- **Settling Time 充足**：恒压阶段需要时间稳定，过短会导致提前判停。
- **采样周期**：建议 ≥ 100ms，避免 N6705C 通信负载过高。
- **QtCharts 缺失降级**：环境无 QtCharts 时图表区降级为纯表格。
- **AI 契约**：实现 5 个能力。
- **Mock 模式**：`DEBUG_MOCK=True` 时全部走 Mock，可走通流程（电流曲线为模拟衰减）。
- **结果文件**：输出到 `Results/charger_iterm/<时间戳>/`。
