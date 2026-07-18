# DCDC Efficiency

测量 BES 芯片 DCDC（BUCK）的**转换效率**，支持固定 Vin 扫 Iout、扫 Vin、扫温度三种模式。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `DCDC Efficiency`
- 对应源码：`ui/pages/pmu_test/pmu_dcdc_efficiency.py`（`PMUDCDCEfficiencyUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：复用 `N6705CConnectionMixin`，显示当前连接的 N6705C 与通道。
- **温箱连接卡片**（温扫模式才用）：`ChamberConnectionMixin`。
- **Test Config 卡片**：
  - Test Mode：`Fixed Vin / Sweep Vin / Sweep Temp`
  - Vin (V)：输入电压
  - Vin Range / Step：扫描范围与步进（Sweep Vin 模式）
  - Iout Range / Step：负载电流扫描范围与步进
  - Temp Points：温度点列表（Sweep Temp 模式）
- **Channel Config 卡片**：选择 N6705C 通道（Vin 接 CH1，Vout 接 CH2，Iout 通过 CH1 电流回读）。

### 2. 右侧图表区
- **Efficiency vs Iout** 曲线（支持 QtCharts 鼠标缩放/平移/Marker）。
- 多条曲线：不同 Vin 或不同 Temp 一条。
- 数据点同步写入下方结果表。

### 3. 底部 — Execution Logs
- 实时打印测试进度、每个扫描点的 Vin/Vout/Iout/Pout/Pin/Efficiency。
- 异常带 `exc_info=True` 详细堆栈。

## 典型操作流程

1. 在 N6705C Analyser 页连接好 N6705C（Vin 通道、Vout 通道）。
2. 进入本页 → Test Mode 选 `Fixed Vin`。
3. 设 Vin=3.8V，Iout Range 0~500mA，Step 50mA。
4. 选择正确的 N6705C 通道映射。
5. 点击 `▷ Start Sequence`。
6. 测试线程逐点扫描，曲线实时增长；日志区打印每个点结果。
7. 测试完成自动保存结果到 `Results/pmu_dcdc_efficiency/<时间戳>/`。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Vin | V | DCDC 输入电压 |
| Iout Range | mA | 负载电流扫描范围 |
| Step | mA | 扫描步进 |
| Efficiency | % | Pout / Pin × 100% |

## 注意事项

- **QtCharts 缺失降级**：若环境无 `PySide6.QtCharts`，曲线区会降级为只显示结果表（`HAS_QTCHARTS=False`）。
- **Sweep Temp 模式**：必须先在 Chamber 页连接温箱；每个温度点会等待稳定后再扫描 Iout。
- **AI 高风险动作**：`Start Sequence` 已注册为 AI 可触发动作，AI 调用前会请求确认。
- **数据平滑**：曲线可选 `savgol_smooth` 平滑（Savitzky-Golay 滤波）。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C 与温箱走 Mock，可无硬件走通流程。
