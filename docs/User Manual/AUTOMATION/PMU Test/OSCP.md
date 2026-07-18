# OSCP

OSCP（Over-Shoot Current Protection，过冲保护）测试：监测芯片在特定事件触发时 PMU 状态寄存器的位变化，验证过冲保护功能是否正常触发与恢复。

## 页面入口

- 导航栏 → `AUTOMATION` → `PMU Test` → 子菜单 `OSCP`
- 对应源码：`ui/pages/pmu_test/pmu_oscp_ui.py`（`PMUOSCPUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，提供主电源。
- **I2C Config 卡片**：USB-I2C 设备地址、速度模式。
- **Test Config 卡片**：
  - Monitor Register Address：监测的寄存器地址（hex）
  - Bit Mask：关注位掩码
  - Trigger Event：触发过冲的事件类型（外部中断 / GPIO 翻转等）
  - Monitor Duration (ms)：监测窗口时长
- **CardFrame 卡片**：紧凑布局（10,8,10,8 内边距）。

### 2. 右侧监测面板
- 实时位变化表：每行一次采样，列出 `bit_field` / `old_value` / `new_value` / `changed_bits`。
- 监测时间线：高亮保护触发与恢复的时间点。

### 3. 底部 — Execution Logs
- 打印 I2C 读取流、检测到位变化的事件、`get_changed_bits` / `format_changed_bits` 输出。

## 典型操作流程

1. 连接 N6705C（主电源）+ USB-I2C（控制 PMU 寄存器）。
2. 进入本页 → 输入监测寄存器地址（如 `0x1A`）与关注位掩码（如 `0x06`）。
3. 选择触发事件类型。
4. 设 Monitor Duration 500ms。
5. 点击 `▷ Start`。
6. `OSCPMonitorWorker` 启动：注入触发事件 → 持续轮询寄存器 → 检测位变化 → 记录时间线。
7. 测试结束输出报告：保护是否触发 / 触发时刻 / 恢复时刻 / 持续时长。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Register Address | hex | 监测的 PMU 状态寄存器地址 |
| Bit Mask | hex | 关注的位（其余位忽略） |
| Monitor Duration | ms | 监测窗口时长 |
| Trigger Event | — | 触发过冲的事件类型 |

## 注意事项

- **地址解析**：`parse_hex_address` 支持 `0x1A` 与 `1A` 两种格式。
- **位变化格式化**：`format_changed_bits` 输出形如 `bit[2]: 0→1, bit[1]: 1→0`。
- **测试结束信号**：本页发射 `sequence_execution_finished(bool, str)`，MainWindow 的 AI 续跑机制监听该信号回灌 pending 任务。
- **AI 契约**：实现 5 个能力。
- **Mock 模式**：`DEBUG_MOCK=True` 时 I2C 走 MockI2C，N6705C 走 MockN6705C，可走通监测流程（寄存器值为模拟）。
- **不要硬编码 I2C 地址**：地址必须来自配置输入，禁止写入代码。
