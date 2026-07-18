# CLK Test

CLK Test 测试 BES 芯片**时钟频率与性能**，含三个测试项：`cap_freq`（Ctrim vs Frequency）、`temp_freq`（Temperature vs Frequency）、`clk_perf`（Clock Performance Analysis，支持 CSV 导入）。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `CLK Test`
- 对应源码：`ui/pages/pmu_test/clk_test_ui.py`（`CLKTestUI`）

## 界面布局

### 1. 左侧配置区
- **Oscilloscope 连接卡片**：`OscilloscopeConnectionMixin`，频率测量源。
- **Chamber 连接卡片**：`ChamberConnectionMixin`（temp_freq 项需要）。
- **Keysight 53230A 连接卡片**：`Keysight53230AConnectionMixin`，高精度频率计（可选）。
- **Test Config 卡片**：
  - Test Item 下拉：`cap_freq` / `temp_freq` / `clk_perf`
  - 子配置随测试项切换：
    - cap_freq：Ctrim 扫描范围、步进
    - temp_freq：温度点列表、目标频率
    - clk_perf：CSV 文件路径（导入模式）

### 2. 右侧图表区
- pyqtgraph 绘制的频率曲线。
- `cap_freq`：Frequency vs Ctrim Code
- `temp_freq`：Frequency vs Temperature
- `clk_perf`：从导入的 CSV 重建频率漂移曲线

### 3. 底部 — Execution Logs
- 打印每次 Ctrim/温度设置的 I2C 写入、示波器/频率计读数、与目标频率的偏差。

## 典型操作流程

### cap_freq（Ctrim 校准）
1. 连接示波器（或 53230A）+ USB-I2C。
2. Test Item 选 `cap_freq`。
3. 设 Ctrim 扫描范围 0~63，步进 1。
4. `▷ Start Sequence` → 每个 Ctrim 值写入 → 频率计读数 → 绘制曲线。
5. 找到使频率最接近目标的 Ctrim 值，输出推荐配置。

### temp_freq（温度漂移）
1. 先在 Chamber 页连接温箱。
2. Test Item 选 `temp_freq`。
3. 设温度点列表与目标频率。
4. `▷ Start` → 每个温度点等待稳定 → 读频率 → 绘制温度漂移曲线。

### clk_perf（CSV 分析）
1. Test Item 选 `clk_perf`。
2. 选择已采集的 CSV 文件。
3. 页面解析 CSV → 重建曲线 → 显示统计（峰峰值、均值、最大漂移）。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Ctrim Code | — | 时钟修整码（典型 6 位，0~63） |
| Frequency | Hz | 示波器/频率计实测频率 |
| Target Frequency | Hz | 期望频率，用于评估偏差 |
| Temperature Points | °C | temp_freq 测试的温度点列表 |

## 注意事项

- **频率计优先**：连接了 53230A 时优先使用其高精度读数；未连接则用示波器 `FREQUENCY` 测量项。
- **CSV 格式**：`clk_perf` 导入的 CSV 需包含 `timestamp` 与 `frequency` 两列。
- **结果保存**：测试结果输出到 `Results/pmu_clk/<时间戳>/`，含 CSV 与图表 PNG。
- **未实现 AI 契约**：本页面未注册 `ai_capabilities`，AI 助手无法读写其配置（如需扩展请补齐 `CAP_*` 实现）。
- **Mock 模式**：`DEBUG_MOCK=True` 时示波器/温箱/频率计走 Mock。
- **多 Mixin 继承**：本页同时继承 3 个仪器 Mixin，连接状态由各自管理。
