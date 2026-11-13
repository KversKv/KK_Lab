# instruments/ — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../AGENTS.md) 硬红线。仅存放本模块局部知识；通用规范回指 docs/ai。

## 加载指针（AI 按需拉取）

- **新增 / 修改仪器驱动** → @see [docs/ai/05_INSTRUMENT_GUIDE.md](../docs/ai/05_INSTRUMENT_GUIDE.md)
- **查 IT2700 系列 SCPI 指令** → 直接 grep 手册提取文本 [tests/_it2700_prog_guide.txt](../tests/_it2700_prog_guide.txt)（源 PDF 在 `Temp_Docs/IT2705/IT2700 Programming Guide-CN.pdf`，勿重复提取）
- **查 N6705C 系列 SCPI 指令** → 直接 grep 手册提取文档 [power/keysight/n6705c_programming_guide/](./power/keysight/n6705c_programming_guide/)（源 PDF 在 `Temp_Docs/N6705C_编程指南.pdf`，重新提取用 `tests/extract_n6705c_pdf.py`，勿重复提取）
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
- N6705C / IT2705 经 factory 创建后必须刷新 `channel_module_models` 并提供 `is_channel_supported(ch)`；空槽、未知型号或单通道查询失败仅禁用该通道，Mock 同步实现。
- N6705C 逐通道用 `:SYSTem:CHANnel:MODel? (@ch)` 查询型号；IT2705 先批量 `:SYSTem:CHANnel:STATus? (@1,2,3,4,5,6,7,8)`，仅对状态 `1` 的通道查型号，空槽禁止再查 `MODel?`；禁用短格式和 `SYST:MOD:MOD?`。
- **IT2705 对 N6705C 的 parity 方法（2026-11 补）**：`set_sense_mode`=`SENS ON/OFF,(@ch)`（手册 §15 `SENSe[:REMote][:STATe]`）；`set_voltagemode`=`EMUL VMETer`；`prepare_force_high/prepare_force_auto/restore_channels_to_vmeter` 与 N6705C 同语义纯组合（VMETer→测压→PS2Q+定值+限流）；`set_channel_range(_off)` 为 **no-op**——IT2700 SENSe 子系统无电流量程/自动量程命令（仅 `SENS:VOLT:RANG:AUTO`），业务侧直接调用勿删。
- **IT2705 开路基线（真机 2026-11）**：VMETer+channel_on 开路测量饱和在 **-20.4V**（负满幅），`prepare_force_*` 在开路台架上测到的是该饱和值；接 DUT 时 VMETer 读真实轨压。`VOLT` 写超量程/负值被仪器**静默拒绝**（`VOLT?` 保持上一接受值），CCLoad 开路测得 ≈0 正小值。

## 局部约定

- **驱动布局**：`instruments/<类型>/<厂商>/<型号>.py`；类型目录：`scopes/`、`power/`、`chambers/`、`digitMultimeter/`、`frequencyCounter/`、`MCU_IO/`、`wirelessConnectivityTester/`。
- **工厂唯一入口**：[factory.py](./factory.py) 提供 `create_instrument / create_oscilloscope / create_power_analyzer / create_chamber / create_frequency_counter / create_digital_multimeter / create_wireless_tester / create_mcu_io`。新增仪器必须在此注册。
- **Mock 强制**：新驱动必须同步在 [mock/mock_instruments.py](./mock/mock_instruments.py) 添加 `MockXxx`，接口与真实驱动完全一致（鸭子类型）。见 ADR [001-mock-instrument](../docs/ai/decisions/001-mock-instrument.md)。
- **VISA 后端**：禁止在驱动层写死 `pyvisa.ResourceManager('@py')`；默认 `ResourceManager()`，构造函数提供 `visa_library` 可选参数，打开失败回退 `'@py'`。详见 03_GOTCHAS §21。
- **地址禁硬编码**：VISA / 串口地址由 UI 扫描 + 用户选择后传入，禁止写死（驱动构造 / 工厂均强制传参，空地址抛 `ValueError`；`__main__` 演示一律走 `KK_LAB_*_RESOURCE` 环境变量）。实验室预填地址唯一事实源 = `resources/instrument_addresses.json`，UI 经 `core.instruments.address_presets.get_address_preset(group, key)` 读取，缺失返回空串。
- **DSOX4034A 强制触发时基扫描封装（2026-09-04 新增）**：[scopes/keysight/dsox_fast_capture.py](./scopes/keysight/dsox_fast_capture.py) 的 `DSOXFastCapture`（组合复用 DSOX4034A 实例，不经 factory、无 Qt）：无触发源场景（LDO/DCDC 输出）用「`STOP`→改时基→`*OPC?`→`SINGle`→微预填(≈2ms)→`FORCe`(失败回退 `*TRG`)→轮询 `OPERegister:CONDition?` RUN 位(bit3)清零」替代 RUN/STOP+固定 settle；一次性配置 HEADer OFF / ACQuire:TYPE NORMal / TIMebase:MODE MAIN / **REFerence LEFT**（预触发占比≈0，FORCe 可立即发出）/ SWEep NORMal（关 Auto 防自动触发旧帧）/ MEASure:STATistics OFF / ACQuire:POINts 最小值 + 关未用通道与 Math/FFT。完成判据轮询间隔 = max(5ms, 0.02×10×TB)，OPER 连续 3 次解析失败回退 `:RSTate?`；每点 VISA timeout 动态设置（查表或 1.3×(SPAN+0.06)+2.0s）用完恢复；判据超时重试 1 次；`read_measurements()` 单条复合查询批量读值（`;` 拼接、逐条 read），9.9E+37 置 None 并记 `last_invalid`；`calibrate()` 逐档 20 次取 P95×1.2 存 `timeout_table`（查表仅兜底 timeout，实际等待仍由判据决定）；`run_sweep()` 按时基从小到大执行。注意：`configure_once()` 改仪器全局状态（HEADer OFF 等）不复位，与依赖 HEADer ON 的脚本不要混用。

## 局部坑点

> 详细背景见 [docs/ai/03_GOTCHAS.md](../docs/ai/03_GOTCHAS.md) 对应章节。

- **§6 断线重连**：`is_connected()` 不假设恒真；`read/write` 前要有超时保护，异常落盘日志并通知 UI。
- **§13 温箱 Modbus CRC**：VT6002 用 Modbus RTU（CRC16），串口参数需严格匹配；超时建议 2–3s（默认 1s 不够）。
- **温箱串口瞬时中断（WriteFile AccessDenied / WinError 5）**：USB-RS485 受压缩机强电干扰 / USB 电源管理挂起会瞬时拒写，pyserial 抛 `SerialException("WriteFile failed ...")`，重开串口（`disconnect()+connect()`）即可恢复；`TemperatureStabilizer` 新增 `max_read_failures`（默认 0=不限制，>0 时连续 N 次 PV 读失败抛 RuntimeError）防止稳定等待期串口断开还静默干等到 watchdog。
- **§14 N6705C Datalog 格式**：二进制 + CSV 混合，解析走 [power/keysight/n6705c_datalog_process.py](./power/keysight/n6705c_datalog_process.py)，不要重复造轮子。
- **VISA 数值响应禁用 `[:-1]` 去换行**：必须用 `strip()`，否则无换行时会截掉科学计数法指数末位（`E-01 → E-0`，读数放大 10 倍）。
- **IT2705 PS 模式限流前提 = 电压优先（真机 2026-11）**：`CURR:LIM` 是**电压优先**（`FUNC VOLT`）下才生效的限流值；电流优先（`FUNC CURR`）时 PS 通道按 `CURR` 定值输出，限流不起作用。优先级不随 `EMUL` 切换重置（面板可改），`set_mode(PS4Q/PS2Q/PS1Q)` 已自动补写 `FUNC VOLT`；显式控制用 `set_function(ch, "VOLT"/"CURR")`。另：`CURR?` 读回值随优先级变化——电压优先下镜像 `CURR:LIM`，电流优先下才是电流定值。
- **IT2705 MEAS 耗时 = 通道积分时间（真机 2026-11）**：`MEAS:*?` 按 `SENS:APER` 积分开后才返回，面板可设到 20.48s（NPLC 1024），远超 VISA 10s 超时——超时后迟到响应污染 socket 缓冲，后续读写全部错位，仪器报 Query Interrupted/Invalid Command。`measure_voltage/current/power` 已封装"查 APER→>0.02 临时压到 0.02→测量→恢复"（`MEAS_APER_FAST`），APER 查询按通道 5s TTL 缓存（`MEAS_APER_CACHE_TTL_S`，面板手动改 APER 最坏 5s 后自愈）；输出 OFF 时测量返回 `nan`，`_query_float` 视为无有效测量值抛 ValueError。`FETC:*?` 仅返回已完成采集的缓存，不能替代实时测量。
- **IT2705 ELOG 外部记录仪（真机 2026-11 实测，波形采样唯一可行路径）**：`SENS:ELOG:PER` 实测范围 **20us–60s**（手册写 0.0001–1 不准）；`FETC:ELOG? N,(@ch)` 返回记录数组（V/I 同记录配对，MINM 须 OFF 保持紧凑），**仅运行中可读、ABOR 即清空**（收尾必须先排空再 ABOR）；`maxrecords >30000` 仪器无响应（用 ≤20000 分块）、**chanlist 多通道超时**（逐通道取）；二进制取数用 `FORM REAL`+`FORM:BORD NORM`（=大端）：**`start_elog` 一次性切换、`stop_elog` 统一恢复 `FORM ASC`**（逐次取数切换会多 3 次往返/通道），`fetch_elog_records` 须在 start 之后调用。对比：内部 DLOG `FETC:DLOG:*` 只回统计量（均值/最值，数据在机内文件无 SCPI 读回口），`SENS:DLOG:TIME` 仅接受整数秒（写 0.2 读回 0）；DLOG/ELOG 的 FUNC 配置对空槽通道会报 502，仅对在位的通道下发。驱动封装 `configure_elog/start_elog/fetch_elog_records/stop_elog`（[power/itech/it2705.py](./power/itech/it2705.py)），Mock 同步仿真。
- **§15 示波器截图差异**：DSOX4034A 用 `:DISP:DATA? PNG, COLor`；MSO64B 用 `HARDCopy` 系列。基类保留 `capture_screen(path)`，子类各自实现。
- **§21 VISA 后端选择**：USBTMC 仪器在 Windows 上由 NI-VISA / Keysight IO 接管，`pyvisa-py` 会抛 `No device found.`。新增驱动自检：搜 `ResourceManager('@py')` 一律替换为"默认 + 可选 visa_library + 失败回退 @py"。
- **§43 任何 `rm.close()` 禁调用**：pyvisa `ResourceManager.close()` 会连带关闭该 RM 创建的所有资源，IVI 后端 RM 进程级共享（@py 实测同样跨 RM 误伤）——驱动 `disconnect()` 只 `instr.close()`，扫描/探测只关自己开的 session；已全量清理，新代码照此办理。
- **§9 DEBUG_MOCK**：改值后必须重启应用；新增仪器忘加 Mock 会在 Mock 模式崩溃。
- **N6705C ARB 电流脉冲（真机验证 2026-07）**：`ABOR:TRAN` 必须带通道列表（裸写报 `-109 Missing parameter`，故 `arb_stop(channel=None)` 默认 `(@1,2,3,4)`）；`ARB:CURR:PULS` 三段时序被仪器强制 `t0+t1+t2 == 1/freq`，不满足按比例自动压缩，`t2=0` 即零顶部宽度（无脉冲）；50% 占空取 `t0=T/2, t1=0, t2=T/2`（对应面板字段 t0=start / t1=top / t2=end）。
- **DSOX4034A DISPlay 测量 settle 按时基自适应（2026-09-04 真机；2026-09-07 补 STOP 态）**：`_measure_query` 的 pre_cmd 添加测量项会触发 DSOX **RUN 态**全屏重捕，值须等 **16×时基** 才有效；原固定 `settle_s=0.2` 只覆盖 ≤12.5ms/div（大时基如 50ms/div 需 0.8s，Module Test Load Transient 阶段二 @10Hz 曾恒取 9.9e37 整组记 0，且每次重试重发 pre_cmd 重触发重捕永不收敛）。现 `_measure_query` 内已改为 `max(settle_s, 16×当前时基)`，但 **`_meas_refresh_s` 在 STOP 态（`is_acquiring()` False）返回 0**——STOP 态测量对冻结帧直接计算、无重捕（2026-09-07 实测 transient 逐组 stop 定格后连测 4 值，500ms/div 时基旧版白等 4×8s），故"先 stop 定格再测量"可绕过 16× 等待；时基/状态读取失败退回固定值，上层勿再依赖"0.2s 后必有效"假设（RUN 态下仍须 16×）；MSO64B 走 `MEASUrement:IMMed` 即时测量不受影响。
- **CH9114F 高阻语义（2026-09-07 真机）**：`CH910x_GpioConfig` 的 `iFuncSet=0` 会把引脚交回芯片**默认功能**（UART 等自带输出驱动/上下拉），**并非高阻**；真高阻 = `iFuncSet=1`（保持 GPIO 功能，脱离默认功能及其上下拉）+ `iSetDirOut=0`（去输出、置输入，浮空）。[MCU_IO/ch9114f.py](./MCU_IO/ch9114f.py) 的 `hiz()/set_input()` 已按此实现（`set_input` 默认 `gpio_func=True`）；DLL 无独立上下拉 API，`in_pull` 的 up/down 对 CH9114F 等同浮空输入，勿在 CH9114F 场景依赖上下拉语义。
