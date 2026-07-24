# ui/pages/chamber — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **温箱驱动** → [instruments/chambers/](../../../instruments/chambers/)（vt6002 / mt3065 / wt2040）
- **Modbus CRC 坑** → @see [docs/ai/03_GOTCHAS.md §13](../../../docs/ai/03_GOTCHAS.md)
- **用户手册** → `docs/User Manual/INSTRUMENTS/Chamber.md`

## 本模块职责与边界

- **职责**：通用温箱控制页（温度设置 / 读取 / 程序段运行）。
- **上游**：`ui/main_window.py`；**下游**：`instruments/factory.create_chamber`（Modbus / 网口）。
- **铁律**：UI 仅交互；温度读写 / 稳定等待走后台。

## 接口契约（对外不可破坏）

- 经 `create_chamber(chamber_type, port, baudrate, resource)` 创建；支持型号选择 + 串口搜索。
- `InstrumentStatePoller` 周期回读仪器状态。

## 局部约定

- **顶部 `sys.path` 注入**：兼容 `python ui\pages\chamber\chamber_control_ui.py` 直接运行（见 03§22 同款模式）。
- 温箱型号（VT6002 Modbus / MT3065 / WT2040 网口）经下拉选择，地址禁硬编码。

## 局部坑点

- **§13 Modbus CRC**：VT6002 用 Modbus RTU（CRC16），串口参数严格匹配；超时建议 2–3s（默认 1s 不够）。
- **§7 温度稳定等待分钟级**：必须异步，禁主线程阻塞。
- SVG 图标禁 `setDevicePixelRatio`（03§23）。
