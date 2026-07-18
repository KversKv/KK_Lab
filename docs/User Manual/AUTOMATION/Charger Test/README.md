# Charger Test

Charger Test 是 BES 芯片**充电器（Charger）模块**的自动化测试套件，含 4 个子页面，覆盖配置寄存器遍历、状态寄存器读取、终止电流测试与调压精度测试。

## 子页面索引

| 子页面 | 测试目标 | 主要仪器 |
|---|---|---|
| [Config Traverse Test](./Config%20Traverse%20Test.md) | 充电器配置寄存器全遍历验证 | N6705C + I2C |
| [Status Register Test](./Status%20Register%20Test.md) | 状态/故障寄存器读取与判定 | N6705C + 温箱 + I2C |
| [Iterm Test](./Iterm%20Test.md) | 终止电流（Iterm）精度测试 | N6705C + I2C |
| [Regulation Voltage Test](./Regulation%20Voltage%20Test.md) | 调压（VREG）精度测试 | N6705C + I2C |

## 页面入口

- 导航栏 → `AUTOMATION` → `Charger Test` → 悬停展开子菜单选择具体测试项。
- 对应源码：`ui/pages/charger_test/charger_test_ui.py`（容器，隐藏顶部 Tab，由子菜单切换）。

## 共用约定

- **仪器连接**：所有子页面通过 `N6705CConnectionMixin` / `ChamberConnectionMixin` 复用仪器会话。
- **I2C 配置**：通过 USB-I2C 控制充电器寄存器（设备地址、速度模式、10/16 位地址宽度由 `I2CWidthFlag` 配置）。
- **测试线程**：QThread Worker 异步执行，可中途 Stop。
- **AI 契约**：所有子页面实现 `ai_capabilities()` 提供 5 个能力（APPLY_CONFIG / GET_CONFIG / GET_RESULT / START_TEST / STOP_TEST）。
- **结果文件**：测试结果输出到 `Results/charger_<测试项>/<时间戳>/`，含 CSV 与图表截图。
- **状态寄存器映射**：状态/故障位定义见 `status_register_test.py` 的 `STATUS_REGISTER_MAP` 字典（CHG_STAT / VBUS_STAT / PG_STAT / THERM_STAT / WATCHDOG_FAULT / BOOST_FAULT / CHRG_FAULT / BAT_FAULT 等）。
