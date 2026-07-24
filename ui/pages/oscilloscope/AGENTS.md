# ui/pages/oscilloscope — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **示波器自动识别策略** → @see ADR [002-oscilloscope-auto-detect](../../../docs/ai/decisions/002-oscilloscope-auto-detect.md)
- **数值控件单位规范** → @see [docs/ai/01_CONVENTIONS.md §6.3](../../../docs/ai/01_CONVENTIONS.md)
- **示波器驱动** → [instruments/scopes/](../../../instruments/scopes/)

## 本模块职责与边界

- **职责**：示波器统一控制页（自动识别 DSOX4034A / MSO64B），测量 / 触发 / 截图 / 反相。
- **上游**：`ui/main_window.py`；**下游**：`core/controllers/OscilloscopeControllerEx`、`instruments/factory.create_oscilloscope`。
- **铁律**：UI 仅交互；SCPI 一律经 controller → factory，禁直连 VISA。

## 接口契约（对外不可破坏）

- **自动识别**：`*IDN?` 关键字分派（`KEYSIGHT,DSO-X`→`dsox4034a`、`TEKTRONIX,MSO`→`mso64b`），再 `create_oscilloscope(type, resource)`。
- 只依赖 `OscilloscopeBase` 基类 API（`measure_channel` / `capture_screen` 等），品牌差异封装在驱动子类。
- `OscilloscopeControllerEx`（core）封装连接 / 测量 / 截图粗粒度操作。

## 局部约定

- **单位语义随型号动态切换**：Keysight 用秒、Tektronix 用百分比；label 与占位符随连接仪器动态更新（参考 `_update_time_offset_mode`）。
- **多单位输入**（`100us/0.5ms/1s`）：维护"上次单位"记忆（`TimeScaleEdit._last_unit_mult`），无单位纯数字复用上次倍率，**不默认按基本单位解释**；解析成功动态更新 label 单位。
- 测量结果卡按数值自动选档（V/mV/µV、Hz/kHz/MHz/GHz），参考 `_format_measurement_value_split`。

## 局部坑点

- **§15 截图指令差异**：DSOX 用 `:DISP:DATA? PNG, COLor`；MSO64B 用 `HARDCopy` 系列。基类留 `capture_screen`，子类各自实现。
- 截图加载用 `CaptureLoadingOverlay`；SVG 图标禁 `setDevicePixelRatio`（03§23）。
- 新增型号：驱动继承 `OscilloscopeBase` + factory 注册 + 自动识别逻辑加关键字（三处同步，见 ADR 002）。
