# DCDC Module Test

DCDC 模块测试页，绑定 `DCDC_ITEMS` 注册表，对芯片内各 DCDC（BUCK）执行效率、瞬态响应、纹波、PSRR 等测试项。

## 页面入口

- 导航栏 → `AUTOMATION` → `Module Test` → 子菜单 `DCDC`
- 对应源码：`ui/pages/module_test/dcdc_test_ui.py`（`DCDCTestUI`）
- Page Key：`module_test_dcdc`

## 界面布局

继承自 `ModuleTestSubPageBase` 通用框架，与 LDO 页结构一致：

### 1. 顶部仪器连接区
- N6705C / Oscilloscope / Chamber 三个 Mixin 卡片。

### 2. 左侧 — 测试项配置区
- **Test Items Table**：列出 `DCDC_ITEMS` 中所有测试项。
- 测试项典型含：效率扫描、负载瞬态、纹波测量、PSRR、线性/负载调整率。

### 3. 右侧 — 结果展示区
- 效率曲线、瞬态波形、纹波 FFT 等动态切换。

### 4. 底部 — Execution Logs

## 典型操作流程

1. 连接 N6705C（Vin 通道、Vout 通道、Iout 通过 Vin 通道电流回读）+ 示波器（探测 Vout 纹波/瞬态）。
2. 进入本页 → 勾选测试项（如 BUCK_01 效率扫描、BUCK_01 负载瞬态）。
3. 配置每项参数（Vin、Iout 范围、瞬态阶跃、采样率等）。
4. `▷ Start Sequence`。
5. `DCDCTestRunner` 逐项执行，结果写入摘要表。
6. 测试完成保存 HTML 报告 + CSV。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Vin | V | DCDC 输入电压 |
| Vout | V | DCDC 输出电压 |
| Iout | mA | 负载电流（效率扫描时扫范围） |
| Load Step | mA | 负载瞬态阶跃幅值 |
| Slew Rate | A/μs | 负载瞬态摆率 |
| Ripple | mV | 实测输出纹波峰峰值 |

## 注意事项

- **Runner 解耦**：`DCDCTestRunner` 同样是纯函数实现，独立可运行。
- **不要再耦合 PMU Worker**：早期版本曾复用 PMU 的 DCDC Efficiency Worker，造成 Qt 耦合，已重构为独立 Runner。
- **测试项扩展**：在 `core/module_test/dcdc/items.py::DCDC_ITEMS` 注册。
- **AI 契约**：实现 5 个能力。
- **Mock 模式**：`DEBUG_MOCK=True` 时全部走 Mock。
- **结果文件**：输出到 `Results/module_test_dcdc/<时间戳>/`，含 HTML 报告 + CSV + 波形 PNG。
