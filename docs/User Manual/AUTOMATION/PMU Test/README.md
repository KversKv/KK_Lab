# PMU Test

PMU Test 是 BES 芯片 **PMU（Power Management Unit）** 的自动化测试套件，包含 6 个子页面，覆盖效率、输出电压精度、电流源增益、过冲保护、ADC 采样与时钟性能。

## 子页面索引

| 子页面 | 测试目标 | 主要仪器 |
|---|---|---|
| [DCDC Efficiency](./DCDC%20Efficiency.md) | DCDC 转换效率（Vin/Iout 扫描） | N6705C |
| [Output Voltage](./Output%20Voltage.md) | LDO/BUCK 输出电压精度 | N6705C + I2C |
| [Is_gain](./Is_gain.md) | 电流源增益 | N6705C + 示波器 |
| [OSCP](./OSCP.md) | OSCP（过冲保护）监测 | N6705C + I2C |
| [GPADC Test](./GPADC%20Test.md) | GPADC 采样精度 | N6705C + 温箱 + 串口 |
| [CLK Test](./CLK%20Test.md) | 时钟频率与性能 | 示波器 + 频率计 + 温箱 |

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 悬停展开子菜单选择具体测试项。
- 对应源码：`ui/pages/pmu_test/pmu_test_ui.py`（容器，隐藏顶部 Tab，由子菜单切换）。
- 6 个子页面对应 `pmu_dcdc_efficiency.py` / `pmu_output_voltage.py` / `pmu_isGain_ui.py` / `pmu_oscp_ui.py` / `gpadc_test_ui.py` / `clk_test_ui.py`。

## 共用约定

- **仪器连接**：所有子页面通过 `N6705CConnectionMixin` / `OscilloscopeConnectionMixin` / `ChamberConnectionMixin` / `SerialComMixin` 复用 `n6705c_top` / `mso64b_top` / 温箱会话，无需重复连接。
- **布局**：左侧配置卡片 + 右侧图表/结果表 + 底部 `ExecutionLogsFrame` 日志区，日志区可通过 `QSplitter(Qt.Vertical)` 隐式手柄调节高度。
- **测试线程**：所有测试项通过 QThread Worker 异步执行，UI 不阻塞；`Start` 按钮按下后变为 `Stop`，可中途取消。
- **AI 契约**：所有子页面实现 `ai_capabilities()` 提供 `CAP_APPLY_CONFIG` / `CAP_GET_CONFIG` / `CAP_GET_RESULT` / `CAP_START_TEST` / `CAP_STOP_TEST`，AI 助手可读写配置、启停测试、读取结果。
- **AI 回填可视化**：被 AI 修改的输入控件会临时高亮绿色边框 1.5 秒。
- **结果文件**：测试结果输出到 `Results/<测试项>/<时间戳>/`，含 CSV 与图表截图。

## 切换方式

1. 悬停 `PMU Test` 按钮 → 右侧出现子菜单。
2. 选择子菜单项（如 `DCDC Efficiency`）。
3. 子菜单选中状态保留，下次进入回到上次子页。
