# Output Voltage

测量 BES 芯片 LDO / BUCK 的**输出电压精度**：通过 I2C 设置目标电压，由 N6705C 回读实际输出，计算误差。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `Output Voltage`
- 对应源码：`ui/pages/pmu_test/pmu_output_voltage.py`（`PMUOutputVoltageUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：选择回读通道。
- **I2C Config 卡片**：
  - DLL Path：USB-I2C DLL 路径
  - Device Address：I2C 设备地址（默认按芯片配置）
  - Speed Mode：100K / 400K / 1M
- **Test Config 卡片**：
  - LDO/BUCK 列表（多选）
  - Voltage Range / Step：每个模块的电压扫描范围与步进
  - Settling Time (ms)：每次设置后等待稳定的时间

### 2. 右侧图表区
- **Vout vs Vset** 曲线（理想线 + 实测线）。
- **Error (mV) vs Vset** 曲线。
- QtCharts 缩放/平移交互。

### 3. 底部 — Execution Logs + 结果表
- 表格列：模块 / Vset (V) / Vout (V) / Error (mV) / Error (%) / PASS/FAIL。
- 日志区打印 I2C 写入与 N6705C 回读过程。

## 典型操作流程

1. 在 N6705C Analyser 页连接 N6705C，将通道接至待测 LDO 输出。
2. 进入本页 → 配置 I2C 参数（DLL 路径、设备地址、速率）。
3. 勾选要测试的 LDO/BUCK 模块。
4. 设电压范围与步进（如 0.6V ~ 1.2V，步进 50mV）。
5. 点击 `▷ Start`。
6. 线程对每个模块每个电压点：I2C 写入 → 等待 Settling → N6705C 回读 → 记录误差。
7. 测试完成保存 CSV 与图表截图。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Vset | V | I2C 下发的目标电压 |
| Vout | V | N6705C 实测输出电压 |
| Error | mV | Vout - Vset |
| Settling Time | ms | 设置后等待稳定时间，过短会读偏 |

## 注意事项

- **I2C 接口即用即销**：每次操作新建 `I2CInterface`，结束后立即销毁，避免跨线程共享。
- **芯片配置**：LDO/BUCK 列表与电压范围来自 `chips/` 配置，不要在代码中硬编码。
- **Mock 模式**：`DEBUG_MOCK=True` 时 I2C 与 N6705C 走 MockI2C / MockN6705C。
- **AI 契约**：实现 `CAP_APPLY_CONFIG` / `CAP_GET_CONFIG` / `CAP_GET_RESULT` / `CAP_START_TEST` / `CAP_STOP_TEST`，AI 可读写配置与启停测试。
- **AI 回填高亮**：被 AI 修改的输入框会高亮绿色边框 1.5 秒。
