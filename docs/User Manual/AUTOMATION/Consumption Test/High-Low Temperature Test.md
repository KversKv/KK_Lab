# Consumption Test — High-Low Temperature Test

高低温功耗扫描：在多个温度点重复测量 DUT 功耗，绘制功耗-温度曲线。

## 页面入口

- 导航栏 → `AUTOMATION` → `Consumption Test` → 子菜单 `High-Low Temperature Test`
- 对应源码：`ui/pages/consumption_test/high_low_temp_test_ui.py`（`HighLowTempConsumptionTestUI`）

## 界面布局

### 1. 顶部仪器连接区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，电流测量通道。
- **Chamber 连接卡片**：`ChamberConnectionMixin`，温度控制。

### 2. 左侧配置区
- **Temperature Points**：温度点列表（如 -40 / -20 / 0 / 25 / 50 / 85 °C）。
- **Settling Time (min)**：每个温度点到达后的稳定保持时间。
- **Power Modes**：要测量的功耗模式（Normal / Sleep 等）。
- **Sample Period (ms)**：电流采样周期。

### 3. 右侧 — 图表区
- pyqtgraph 绘制 **Current vs Temperature** 曲线（每条曲线一个功耗模式）。
- 支持鼠标缩放、平移。
- 自定义 `ToggleSwitch` 控件切换曲线可见性。

### 4. 底部 — Execution Logs
- 打印温度设置、稳定等待、电流采样、模式切换。
- 异常带 `exc_info=True` 详细堆栈。

## 典型操作流程

1. 在 Chamber 页连接温箱，在 N6705C Analyser 页连接电源分析仪。
2. 进入本页 → 输入温度点列表（如 -40, 25, 85）。
3. 设 Settling Time 10min（让温箱与 DUT 充分热平衡）。
4. 选择要测量的功耗模式（Normal + Sleep）。
5. 点击 `▷ Start`。
6. 线程对每个温度点：
   - 设置温箱目标温度
   - `TemperatureStabilizer` 等待实际温度收敛
   - 保持 Settling Time
   - 切换功耗模式 → N6705C 采样电流 → 记录
7. 测试完成绘制功耗-温度曲线，保存 CSV + 图表 PNG。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Temperature Points | °C | 温度点列表 |
| Settling Time | min | 到达目标后的稳定保持时间 |
| Sample Period | ms | 电流采样周期 |
| Measured Current | mA 或 μA | N6705C 实测电流 |

## 注意事项

- **温度稳定判定**：使用 `TemperatureStabilizer`，等待窗口与容差见 `instruments/chambers/`，不可手动跳过。
- **热平衡**：Settling Time 建议 ≥ 10min，过短会导致 DUT 内部温度未达稳态。
- **多模式切换**：每个温度点会切换所有勾选的功耗模式，模式切换间需留出 Settling Time。
- **未实现 AI 契约**：本子页面未单独注册 `ai_capabilities`，AI 助手不可直接控制；如需 AI 集成请补齐。
- **Mock 模式**：`DEBUG_MOCK=True` 时 N6705C / 温箱走 Mock，温度曲线为模拟。
- **结果文件**：输出到 `Results/consumption_test/<时间戳>/`，含 CSV + 图表 PNG。
