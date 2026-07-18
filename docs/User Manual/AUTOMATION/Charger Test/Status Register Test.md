# Status Register Test

读取并验证充电器**状态寄存器**与**故障寄存器**，支持在指定温度下持续监测，确认状态位与故障位符合预期。

## 页面入口

- 导航栏 → `AUTOMATION` → `Charger Test` → 子菜单 `Status Register Test`
- 对应源码：`ui/pages/charger_test/status_register_test.py`（`StatusRegisterTestUI`）

## 界面布局

### 1. 左侧配置区
- **N6705C 连接卡片**：`N6705CConnectionMixin`。
- **Chamber 连接卡片**：`ChamberConnectionMixin`（温度测试时用）。
- **I2C Config 卡片**：设备地址、速度模式。
- **Test Config 卡片**：
  - Target Status：期望的状态位值（如 CHG_STAT=充电中）
  - Expected Faults：允许出现的故障位（白名单）
  - Forbidden Faults：禁止出现的故障位（黑名单）
  - Monitor Duration (s)：监测时长
  - Temperature Points：温度点列表（可选）

### 2. 右侧结果区
- **状态位时间线**：每个状态位的时间变化曲线。
- **故障位表格**：触发的故障位 + 触发时刻 + 持续时长。

### 3. 底部 — Execution Logs
- 打印每次寄存器读取的完整 hex 值与位解析。

## 状态寄存器位定义

| 寄存器 | 位 | 名称 | 说明 |
|---|---|---|---|
| 0x0B | 7:5 | CHG_STAT | 充电状态（待机/充电中/充满） |
| 0x0B | 4:2 | VBUS_STAT | VBUS 状态（无/USB 适配器/OTG） |
| 0x0B | 1 | PG_STAT | Power Good 状态 |
| 0x0B | 0 | THERM_STAT | 热调节状态 |
| 0x0C | 7 | WATCHDOG_FAULT | 看门狗故障 |
| 0x0C | 6 | BOOST_FAULT | Boost 故障 |
| 0x0C | 5:4 | CHRG_FAULT | 充电故障 |
| 0x0C | 3 | BAT_FAULT | 电池故障 |

## 典型操作流程

1. 连接 N6705C + 温箱（如需）+ USB-I2C。
2. 配置 I2C 参数。
3. 设 Target Status（如 CHG_STAT=充电中）。
4. 在 Forbidden Faults 中勾选 CHRG_FAULT / BAT_FAULT 等致命故障。
5. 设 Monitor Duration 60s。
6. `▷ Start` → 持续读寄存器 → 出现禁用故障即 FAIL → 否则监测满 60s 后 PASS。
7. 测试完成保存报告。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Monitor Duration | s | 持续监测时长 |
| Target Status | — | 期望的状态位组合 |
| Forbidden Faults | — | 出现即判 FAIL 的故障位 |
| Temperature Points | °C | 在多个温度点重复监测 |

## 注意事项

- **温度稳定**：温度点测试使用 `TemperatureStabilizer` 等待稳定。
- **故障位白名单**：某些故障位（如 WATCHDOG_FAULT）在测试期间可允许，列入白名单后不触发 FAIL。
- **AI 契约**：实现 5 个能力。
- **Mock 模式**：`DEBUG_MOCK=True` 时全部仪器走 Mock。
- **结果文件**：输出到 `Results/charger_status_register/<时间戳>/`，含状态时间线 CSV 与图表。
