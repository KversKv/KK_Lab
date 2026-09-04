# instruments/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../AGENTS.md) 硬红线。仅存放本模块局部知识；通用规范回指 docs/ai。

## 加载指针（AI 按需拉取）

- **新增 / 修改仪器驱动** → @see [docs/ai/05_INSTRUMENT_GUIDE.md](../docs/ai/05_INSTRUMENT_GUIDE.md)
- **分层依赖规则** → @see [docs/ai/04_ARCHITECTURE.md](../docs/ai/04_ARCHITECTURE.md)
- **VISA / 打包 / 命令** → @see [docs/ai/02_COMMANDS.md](../docs/ai/02_COMMANDS.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md)

## 本模块职责与边界

- **职责**：纯仪器驱动与协议封装（VISA / 串口 / Modbus / USB），对上层暴露"连接、读写、业务方法"。
- **上游**：`core/`、`ui/` 通过 [factory.py](./factory.py) 拿实例；**禁止**业务代码直接 `import` 具体驱动类。
- **下游**：依赖 `lib/`（I2C / 下载器）、`log_config`、`debug_config`。
- **铁律**：本模块**禁止**任何 `PySide6.QtWidgets` / UI 依赖；耗时 IO 由调用方（core worker）异步化。

## 接口契约（对外不可破坏）

- 所有仪器继承 [base/instrument_base.py](./base/instrument_base.py)，必须实现：`connect()` / `disconnect()` / `is_connected()` / `identify()`。
- VISA 仪器优先继承 [base/visa_instrument.py](./base/visa_instrument.py)。
- 示波器统一走 [scopes/base.py](./scopes/base.py) 的 `OscilloscopeBase`；新增品牌型号须保持 `capture_screen` / `measure_channel` 等基类 API 兼容。
- 业务异常统一抛 [base/exceptions.py](./base/exceptions.py) 中定义的类型。

## 局部约定

- **驱动布局**：`instruments/<类型>/<厂商>/<型号>.py`；类型目录：`scopes/`、`power/`、`chambers/`、`digitMultimeter/`、`frequencyCounter/`、`MCU_IO/`、`wirelessConnectivityTester/`。
- **工厂唯一入口**：[factory.py](./factory.py) 提供 `create_instrument / create_oscilloscope / create_power_analyzer / create_chamber / create_frequency_counter / create_digital_multimeter / create_wireless_tester / create_mcu_io`。新增仪器必须在此注册。
- **Mock 强制**：新驱动必须同步在 [mock/mock_instruments.py](./mock/mock_instruments.py) 添加 `MockXxx`，接口与真实驱动完全一致（鸭子类型）。见 ADR [001-mock-instrument](../docs/ai/decisions/001-mock-instrument.md)。
- **VISA 后端**：禁止在驱动层写死 `pyvisa.ResourceManager('@py')`；默认 `ResourceManager()`，构造函数提供 `visa_library` 可选参数，打开失败回退 `'@py'`。详见 03_GOTCHAS §21。
- **地址禁硬编码**：VISA / 串口地址由 UI 扫描 + 用户选择后传入，禁止写死。
- **DSOX4034A 强制触发时基扫描封装（2026-09-04 新增）**：[scopes/keysight/dsox_fast_capture.py](./scopes/keysight/dsox_fast_capture.py) 的 `DSOXFastCapture`（组合复用 DSOX4034A 实例，不经 factory、无 Qt）：无触发源场景（LDO/DCDC 输出）用「`STOP`→改时基→`*OPC?`→`SINGle`→微预填(≈2ms)→`FORCe`(失败回退 `*TRG`)→轮询 `OPERegister:CONDition?` RUN 位(bit3)清零」替代 RUN/STOP+固定 settle；一次性配置 HEADer OFF / ACQuire:TYPE NORMal / TIMebase:MODE MAIN / **REFerence LEFT**（预触发占比≈0，FORCe 可立即发出）/ SWEep NORMal（关 Auto 防自动触发旧帧）/ MEASure:STATistics OFF / ACQuire:POINts 最小值 + 关未用通道与 Math/FFT。完成判据轮询间隔 = max(5ms, 0.02×10×TB)，OPER 连续 3 次解析失败回退 `:RSTate?`；每点 VISA timeout 动态设置（查表或 1.3×(SPAN+0.06)+2.0s）用完恢复；判据超时重试 1 次；`read_measurements()` 单条复合查询批量读值（`;` 拼接、逐条 read），9.9E+37 置 None 并记 `last_invalid`；`calibrate()` 逐档 20 次取 P95×1.2 存 `timeout_table`（查表仅兜底 timeout，实际等待仍由判据决定）；`run_sweep()` 按时基从小到大执行。注意：`configure_once()` 改仪器全局状态（HEADer OFF 等）不复位，与依赖 HEADer ON 的脚本不要混用。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md) 对应章节。

- **§6 断线重连**：`is_connected()` 不假设恒真；`read/write` 前要有超时保护，异常落盘日志并通知 UI。
- **§13 温箱 Modbus CRC**：VT6002 用 Modbus RTU（CRC16），串口参数需严格匹配；超时建议 2–3s（默认 1s 不够）。
- **§14 N6705C Datalog 格式**：二进制 + CSV 混合，解析走 [power/keysight/n6705c_datalog_process.py](./power/keysight/n6705c_datalog_process.py)，不要重复造轮子。
- **§15 示波器截图差异**：DSOX4034A 用 `:DISP:DATA? PNG, COLor`；MSO64B 用 `HARDCopy` 系列。基类保留 `capture_screen(path)`，子类各自实现。
- **§21 VISA 后端选择**：USBTMC 仪器在 Windows 上由 NI-VISA / Keysight IO 接管，`pyvisa-py` 会抛 `No device found.`。新增驱动自检：搜 `ResourceManager('@py')` 一律替换为"默认 + 可选 visa_library + 失败回退 @py"。
- **§9 DEBUG_MOCK**：改值后必须重启应用；新增仪器忘加 Mock 会在 Mock 模式崩溃。
- **N6705C ARB 电流脉冲（真机验证 2026-07）**：`ABOR:TRAN` 必须带通道列表（裸写报 `-109 Missing parameter`，故 `arb_stop(channel=None)` 默认 `(@1,2,3,4)`）；`ARB:CURR:PULS` 三段时序被仪器强制 `t0+t1+t2 == 1/freq`，不满足按比例自动压缩，`t2=0` 即零顶部宽度（无脉冲）；50% 占空取 `t0=T/2, t1=0, t2=T/2`（对应面板字段 t0=start / t1=top / t2=end）。
- **DSOX4034A DISPlay 测量 settle 按时基自适应（2026-09-04 真机）**：`_measure_query` 的 pre_cmd 添加测量项会触发 DSOX 全屏重捕，值须等 **16×时基** 才有效；原固定 `settle_s=0.2` 只覆盖 ≤12.5ms/div（大时基如 50ms/div 需 0.8s，Module Test Load Transient 阶段二 @10Hz 曾恒取 9.9e37 整组记 0，且每次重试重发 pre_cmd 重触发重捕永不收敛）。现 `_measure_query` 内已改为 `max(settle_s, 16×当前时基)`（`_meas_refresh_s` 读时基失败退回固定值），上层勿再依赖"0.2s 后必有效"假设；MSO64B 走 `MEASUrement:IMMed` 即时测量不受影响。
