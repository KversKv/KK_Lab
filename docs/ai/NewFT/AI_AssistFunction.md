# AI Assistant 接口能力汇总

> 事实源：`core/ai/actions/handlers/*.py`、`core/ai/actions/registry.py`、`core/ai/actions/builder.py`、`core/ai/ai_service.py`
> 说明：AI 一切落地动作必须经 `ActionRegistry → PermissionChecker → 确认 → ActionDispatcher` 闭环；AI 无法直接执行 Python / 读写文件 / 任意网络请求 / 直接操作 Qt Widget。

---

## 1. 受控动作接口（AI 可调用的工具 / function calling）

所有 Action 以 `ActionSpec` 注册（`name` / `description` / `parameters_schema` / `risk_level` / `require_confirmation` / `category`），由 `builder.py` 装配进 registry，并经 `to_tools()` 渲染为 OpenAI tools 提供给模型。

### 1.1 查询类（category=query，全部只读，风险 low）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `get_current_page` | 无 | low | 否 | 获取当前所在页面标识（page_key） |
| `get_serial_status` | 无 | low | 否 | 获取当前活动串口会话状态（端口/波特率/连接/收发字节） |
| `get_recent_serial_logs` | `lines`(1-1000) | low | 否 | 读取活动串口会话最近 N 行接收日志（脱敏+上限保护） |
| `get_recent_app_logs` | `lines`(1-1000) | low | 否 | 读取软件运行日志最近 N 行（环形缓冲） |
| `get_instrument_status` | 无 | low | 否 | 读取已注册仪器会话状态快照（不主动 query 真机） |
| `get_test_sequence_status` | 无 | low | 否 | 获取当前测试序列运行状态（是否运行/暂停/步骤数） |
| `get_waveform_window` | `label`, `t0`, `t1`, `max_points`(10-5000) | low | 否 | 波形按需放大：截取指定通道 [t0,t1] 高分辨率片段（超出 LTTB 压缩） |
| `get_waveform_segments` | `label`, `t0`, `t1`, `pen`(0.1-1000) | low | 否 | 波形段落子结构分析（PELT 变点检测），返回形态标签/均值/峰值/宽度/电荷 |

### 1.2 UI 导航类（category=ui，风险 low）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `open_page` | `page`(枚举) | low | 否 | 切换到指定页面 |
| `toggle_ai_panel` | `open`(bool) | low | 否 | 打开/关闭右侧 AI 助手面板 |

`open_page` 的 `page` 枚举：`power_analyser` / `datalog` / `oscilloscope` / `thermal_chamber` / `pmu_test` / `consumption_test` / `charger_test` / `custom_test` / `vmin_hunter` / `kk_serials` / `collection`。

### 1.3 串口类（category=serial）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `clear_serial_log` | 无 | low | 否 | 清空 AI 侧串口接收日志缓存 |
| `send_serial_text` | `text`, `append_newline`(bool) | high | 是 | 向当前活动串口会话发送一段文本（经 SerialSessionManager） |

### 1.4 仪器类（category=instrument，一律经 InstrumentManager）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `query_instrument` | `session_id`, `command` | low | 否 | 对已连接会话发只读 SCPI 查询（命令须含 `?`） |
| `connect_instrument` | `instrument_type`, `resource`, `role`, `slot` | medium | 是 | 按类型发起异步连接（`connect_async`） |
| `scan_instruments` | `instrument_type` | low | 否 | 异步扫描 + 回灌上次缓存候选 |
| `disconnect_instrument` | `session_id` | medium | 否 | 断开指定仪器会话（异步） |
| `disconnect_all_instruments` | 无 | medium | 是 | 断开所有已连接会话（异步） |
| `find_instrument_sessions` | `role`, `required_capabilities[]` | low | 否 | 按角色/能力查找已连接会话 |
| `get_instrument_capabilities` | `session_id` | low | 否 | 读取会话能力集合 |
| `measure_voltage` | `session_id`, `channel` | low | 否 | 测量通道电压（MEAS:VOLT?） |
| `measure_current` | `session_id`, `channel` | low | 否 | 测量通道电流（MEAS:CURR?） |
| `get_channel_output_state` | `session_id`, `channel` | low | 否 | 读取通道输出开关状态（OUTP?） |
| `get_channel_limits` | `session_id`, `channel` | low | 否 | 读取通道电流/电压限值（CURR:LIM? / VOLT:LIM?） |
| `set_instrument_output` | `session_id`, `channel`, `enabled` | high | 是 | 开/关通道输出（OUTP ON/OFF） |
| `set_instrument_voltage` | `session_id`, `channel`, `voltage` | high | 是 | 设置通道输出电压（VOLT，单位 V） |
| `set_instrument_current` | `session_id`, `channel`, `current` | high | 是 | 设置通道输出电流（CURR，单位 A） |
| `set_current_limit` | `session_id`, `channel`, `limit` | high | 是 | 设置通道电流限值（CURR:LIM，单位 A） |
| `set_output_off_mode` | `session_id`, `channel`, `mode(HIGHZ/LOWZ)` | high | 是 | 设置输出关闭模式（OUTP:TMOD，影响 DUT 安全） |

> 写类高风险动作执行约束：会话须已连接、未被其它 owner 占用；执行期 `try_set_busy` 取短租约后调用驱动方法，驱动内部对量程/SCPI 安全做硬熔断，AI 无法突破。只读测量类（measure_*/get_channel_*）不持租约，但仪器忙时拒绝以免抢占运行中的测试。
> `scan_instruments` 为异步扫描（VISA 探测耗时数秒），handler fire-and-forget 发起 `scan_async` 并回灌上次缓存候选；扫描结果由 `InstrumentManager.get_last_scan` 缓存，AI 再次调用即可取回最新结果。

### 1.5 测试序列类（category=test_sequence，经 custom_test runner）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `start_test_sequence` | 无 | high | 是 | 启动当前页面的测试序列 |
| `pause_test_sequence` | 无 | high | 是 | 暂停/恢复当前运行的测试序列 |
| `stop_test_sequence` | 无 | high | 否（安全操作，仍写审计） | 停止当前运行的测试序列 |

### 1.6 示波器类（category=scope，经 InstrumentManager 取示波器驱动实例）

| 动作 | 参数 | 风险 | 需确认 | 作用 |
|---|---|---|---|---|
| `scope_measure_channel` | `session_id`, `channel` | low | 否 | 一次取 PK2PK/FREQUENCY/VMAX/VMIN 四项（容忍单项失败） |
| `scope_get_measurement` | `session_id`, `channel`, `type` | low | 否 | 按类型取单项测量（pk2pk/frequency/mean/max/min/rms/amplitude） |
| `scope_capture_screen` | `session_id`, `invert` | low | 否 | 截屏 PNG 落盘到 user_data/ai/screenshots/，只回路径/尺寸/状态 |
| `scope_autoscale` | `session_id` | medium | 否 | 一键自动量程（仅 DSOX4034A 支持，MSO64B 优雅失败） |
| `scope_set_timebase` | `session_id`, `seconds_per_div` | high | 是 | 设置时基（秒/格） |
| `scope_set_channel_scale` | `session_id`, `channel`, `volts_per_div` | high | 是 | 设置通道垂直档位（V/格） |
| `scope_set_trigger` | `session_id`, `source`, `level`, `slope` | high | 是 | 设置边沿触发（源通道/电平/斜率 POS/NEG/EITH） |
| `scope_run` | `session_id` | medium | 否 | 连续采集（RUN） |
| `scope_stop` | `session_id` | medium | 否 | 停止采集（STOP） |
| `scope_single` | `session_id` | medium | 否 | 单次采集（SINGLE） |
| `scope_is_acquiring` | `session_id` | low | 否 | 读取采集状态（is_acquiring） |

> 示波器动作复用仪器类 `_run_read_action` / `_run_write_action` 骨架（会话存在 + 已连接 + 未被占用 + 租约管理 + 异常兜底）。读类不持租约，仪器忙时拒绝以免抢占运行中测试；写类持 busy 租约。`scope_capture_screen` 截图为二进制，回灌模型时只回路径/尺寸/状态，图像走 P6 产物通道，不塞进对话上下文（防撑爆 token）。

### 1.7 动作总览

- 已注册动作合计 **42 个**：查询 8 + UI 2 + 串口 2 + 仪器 16 + 示波器 11 + 测试序列 3。
- 风险分布：low 23、medium 7、high 12。
- 需二次确认：`send_serial_text`、`connect_instrument`、`disconnect_all_instruments`、`set_instrument_output`、`set_instrument_voltage`、`set_instrument_current`、`set_current_limit`、`set_output_off_mode`、`start_test_sequence`、`pause_test_sequence`、`scope_set_timebase`、`scope_set_channel_scale`、`scope_set_trigger`。

---

## 2. 能力依赖注入（ActionDeps）

由 UI 层（MainWindow）构造并注入只读访问器与受控操作回调，core 不反向依赖 ui；字段为 None 表示当前环境不支持，handler 优雅降级。

- 只读访问器：`instrument_manager`、`page_key_getter`、`serial_status_getter`、`serial_manager_getter`、`execution_logs_getter`、`app_logs_getter`、`rx_recent_getter`、`test_status_getter`、`waveform_data_getter`。
- 受控操作回调：`open_page_callback`、`toggle_ai_panel_callback`、`serial_send_text_callback`、`serial_clear_callback`、`test_run_callback`、`test_pause_callback`、`test_stop_callback`。

---

## 3. AIService 编排接口（`core/ai/ai_service.py`）

### 3.1 公开方法

| 方法 | 作用 |
|---|---|
| `set_action_system(registry, dispatcher)` | 注入受控动作系统，注入后 send() 默认带 tools 进入 agent 模式 |
| `set_execution_logs_getter(getter)` | 注入执行日志访问器 |
| `set_sequence_data_getter(getter)` | 注入序列数据访问器 |
| `set_serial_status_getter(getter)` | 注入串口状态访问器 |
| `feed_serial_rx(session_id, data)` | 喂入串口 RX 数据到缓存 |
| `set_page_context(page_key)` | 页面切换时切换 Profile 与会话历史 |
| `current_page_key()` / `current_session_key()` | 当前页面/会话标识 |
| `clear_history()` | 清空当前会话历史 |
| `session_stats()` / `persisted_history()` | 会话统计 / 已落盘历史 |
| `available_models()` / `current_model()` / `set_model_override(model)` | 模型列表 / 当前模型 / 临时切换模型 |
| `is_busy()` / `settings` / `dispatcher` / `rx_cache` | 状态与组件属性 |
| `analyze_recent_logs()` / `analyze_logs(options)` | 触发日志分析 |
| `generate_draft(kind, user_text)` | 生成草案（测试配置/脚本草案） |
| `test_connection()` | 测试 New API 连通性 |
| `rate_trace(trace_id, rating)` / `record_feedback(msg_id, rating, comment)` | 经验回流评分/反馈 |
| `start_telemetry()` | 启动 telemetry 上报 |
| `cancel()` / `shutdown()` | 取消当前请求 / 关闭回收 |

### 3.2 信号（Signal）

`response_ready` / `response_started` / `response_delta` / `response_finished` / `analysis_ready` / `draft_ready` / `error_occurred` / `busy_changed` / `connection_tested` / `action_requested` / `action_result` / `usage_updated` / `trace_recorded`。

---

## 4. 安全与边界

- 落地链路：`AIService 组装(Prompt+上下文+tools) → NewAPIClient(QThread) → ResponseParser → ActionRegistry 校验 → PermissionChecker 判风险 → 必要时 ConfirmDialog/Preview → ActionDispatcher 执行 → AuditLog 审计`。
- 风险策略：`PermissionChecker(require_confirm_high=True, allow_critical=False)`，high 默认需确认，critical 默认禁止。
- AI **不**具备：直接执行任意 Python、直接读写文件系统、直接发起任意网络请求、直接操作 Widget。

---

## 5. 接口扩展计划（Roadmap）

> 目标：把当前 31 个动作扩成覆盖「连接管理 → 仪器测量 → 示波器 → 温箱 → 串口 → 测试编排 → 数据导出 → 诊断」的完整接口体系。
> 原则：① 每个规划动作都对应代码库**已存在**的底层能力，避免空中楼阁；② 沿用现有 `ActionSpec` + `ActionDeps` + dispatcher 闭环，不破坏分层；③ 风险等级与确认策略与现有保持一致（写类 high+确认，读类 low）。
> 落地映射依据：仪器驱动 [n6705c.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/power/keysight/n6705c.py)、[dsox4034a.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/scopes/keysight/dsox4034a.py)、[mso64b.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/scopes/tektronix/mso64b.py)、[vt6002_chamber.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/chambers/vt6002_chamber.py)；管理层 [instrument_manager.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/instruments/instrument_manager.py)；测试节点 [instrument_nodes.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/custom_test/nodes/instrument_nodes.py)。

### 5.0 优先级与阶段划分

| 阶段 | 主题 | 价值 | 复杂度 |
|---|---|---|---|
| P1 | 连接管理补全 + 仪器测量读数 | 高（补齐 `connect_instrument`，让 AI 能闭环连接→测量→分析） | 低 |
| P2 | 示波器能力（测量/截图/触发/时基） | 高（波形排障是核心场景） | 中 |
| P3 | 温箱能力（控温/读温/判稳） | 中（温扫测试刚需） | 中 |
| P4 | 串口/会话扩展（多会话/HEX/枚举） | 中 | 低 |
| P5 | 测试编排进阶（草案应用/单步/变量） | 高（与 `generate_draft` 打通） | 高 |
| P6 | 数据导出与产物（截图保存/Datalog/报告） | 中 | 中 |
| P7 | 诊断与自检（错误队列/自检/审计回看） | 中 | 低 |

---

### 5.1 P1 · 连接管理补全（category=instrument）

| 规划动作 | 参数 | 风险 | 需确认 | 落地到 |
|---|---|---|---|---|
| `connect_instrument` | `instrument_type`, `role`, `resource`, `slot` | medium | 是 | `InstrumentManager.connect_async(InstrumentSpec)` |
| `scan_instruments` | `instrument_type` | low | 否 | `InstrumentManager.scan_async` + `scan_finished` 信号 |
| `disconnect_all_instruments` | 无 | medium | 是 | `InstrumentManager.disconnect_all_async` |
| `find_instrument_sessions` | `role`, `required_capabilities[]` | low | 否 | `InstrumentManager.find_sessions` |
| `get_instrument_capabilities` | `session_id` | low | 否 | `InstrumentSnapshot.capabilities` |

> 说明：`connect_instrument` 已在 P1 正式补全注册；扫描结果通过 `scan_finished(instrument_type, candidates)` 异步回灌并由 `InstrumentManager.get_last_scan` 缓存，handler 处理「异步发起 + 轮询取回」模式（与现有 `disconnect_async` 一致）。

**实施进度（P1 连接管理）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `connect_instrument` | ✅ 已完成 | `handlers/instrument.py` | 已在 `SPECS` 注册，medium+确认 |
| `scan_instruments` | ✅ 已完成 | `handlers/instrument.py` | 异步扫描 + `get_last_scan` 缓存回灌 |
| `disconnect_all_instruments` | ✅ 已完成 | `handlers/instrument.py` | medium+确认 |
| `find_instrument_sessions` | ✅ 已完成 | `handlers/instrument.py` | — |
| `get_instrument_capabilities` | ✅ 已完成 | `handlers/instrument.py` | — |

### 5.2 P1 · 仪器测量读数（category=instrument，读类 low）

| 规划动作 | 参数 | 风险 | 落地到（驱动方法） |
|---|---|---|---|
| `measure_voltage` | `session_id`, `channel` | low | `n6705c.measure_voltage` |
| `measure_current` | `session_id`, `channel` | low | `MEAS:CURR?`（驱动测流方法） |
| `get_channel_output_state` | `session_id`, `channel` | low | `n6705c.get_channel_state` |
| `get_channel_limits` | `session_id`, `channel` | low | `get_current_limit` / `get_voltage_limit` |
| `set_current_limit` | `session_id`, `channel`, `limit` | high | `n6705c.set_current_limit`（OCP 边界，必须确认） |
| `set_output_off_mode` | `session_id`, `channel`, `mode(HIGHZ/LOWZ)` | high | `n6705c.set_output_off_mode`（影响 DUT 安全） |

> 读类测量补全后，AI 才能形成「设电压 → 测电流 → 判断 → 调整」的真实闭环，而不是只能写不能读。

**实施进度（P1 仪器测量）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `measure_voltage` | ✅ 已完成 | `handlers/instrument.py` | 读类，经 `_run_read_action` |
| `measure_current` | ✅ 已完成 | `handlers/instrument.py` | 读类 |
| `get_channel_output_state` | ✅ 已完成 | `handlers/instrument.py` | 读类 |
| `get_channel_limits` | ✅ 已完成 | `handlers/instrument.py` | 读类；补全驱动 `get_voltage_limit` |
| `set_current_limit` | ✅ 已完成 | `handlers/instrument.py` | 写类，需确认 |
| `set_output_off_mode` | ✅ 已完成 | `handlers/instrument.py` | 写类，需确认 |

### 5.3 P2 · 示波器能力（新增 category=scope）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `scope_measure_channel` | `session_id`, `channel` | low | `OscilloscopeBase.measure_channel`（PK2PK/FREQ/VMAX/VMIN） |
| `scope_get_measurement` | `session_id`, `channel`, `type` | low | `get_channel_pk2pk/frequency/mean` 等 |
| `scope_capture_screen` | `session_id`, `invert` | low | `capture_screen_png`（返回产物路径，见 P6） |
| `scope_autoscale` | `session_id` | medium | `dsox4034a.autoscale` |
| `scope_set_timebase` | `session_id`, `seconds_per_div` | high | `set_timebase_scale` |
| `scope_set_channel_scale` | `session_id`, `channel`, `volts_per_div` | high | `set_channel_scale` |
| `scope_set_trigger` | `session_id`, `source`, `level`, `slope` | high | `set_trigger_config` |
| `scope_run` / `scope_stop` / `scope_single` | `session_id` | medium | `run` / `stop` / `single` |
| `scope_is_acquiring` | `session_id` | low | `is_acquiring` |

> 截图为二进制，回灌模型时只回路径/尺寸/状态，图像走 P6 产物通道，不塞进对话上下文（防撑爆 token）。

**实施进度（P2 示波器）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `scope_measure_channel` | ✅ 已完成 | `handlers/scope.py` | 读类，PK2PK/FREQUENCY/VMAX/VMIN 容忍单项失败 |
| `scope_get_measurement` | ✅ 已完成 | `handlers/scope.py` | 读类，7 种测量类型 |
| `scope_capture_screen` | ✅ 已完成 | `handlers/scope.py` | PNG 落盘 user_data/ai/screenshots/，回路径/尺寸 |
| `scope_autoscale` | ✅ 已完成 | `handlers/scope.py` | medium，仅 DSOX4034A 支持 |
| `scope_set_timebase` | ✅ 已完成 | `handlers/scope.py` | 写类，需确认 |
| `scope_set_channel_scale` | ✅ 已完成 | `handlers/scope.py` | 写类，需确认 |
| `scope_set_trigger` | ✅ 已完成 | `handlers/scope.py` | 写类，需确认 |
| `scope_run` / `scope_stop` / `scope_single` | ✅ 已完成 | `handlers/scope.py` | medium |
| `scope_is_acquiring` | ✅ 已完成 | `handlers/scope.py` | 读类 |

### 5.4 P3 · 温箱能力（新增 category=chamber）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `chamber_get_current_temp` | `session_id` | low | `vt6002.get_current_temp` |
| `chamber_get_set_temp` | `session_id` | low | `vt6002.get_set_temp` |
| `chamber_set_temperature` | `session_id`, `temperature` | high | `vt6002.set_temperature`（影响 DUT 环境） |
| `chamber_start` / `chamber_stop` | `session_id` | high | `vt6002.start` / `stop` |
| `chamber_wait_stable` | `session_id`, `target`, `tolerance`, `timeout` | high | 复用 [SetChamberTemp 判稳逻辑](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/custom_test/nodes/instrument_nodes.py#L587-L609)（长流程走 worker + busy 租约） |

> `chamber_wait_stable` 是长耗时动作，必须经 QThread worker，禁止阻塞；执行期持 busy 租约，避免其它流程改温度。

**实施进度（P3 温箱）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `chamber_get_current_temp` | ⬜ 未开始 | `handlers/chamber.py`（新建） | 读类 |
| `chamber_get_set_temp` | ⬜ 未开始 | `handlers/chamber.py` | 读类 |
| `chamber_set_temperature` | ⬜ 未开始 | `handlers/chamber.py` | 写类，需确认 |
| `chamber_start` / `chamber_stop` | ⬜ 未开始 | `handlers/chamber.py` | 写类，需确认 |
| `chamber_wait_stable` | ⬜ 未开始 | `handlers/chamber.py` | 长流程，走 worker |

### 5.5 P4 · 串口/会话扩展（category=serial）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `list_serial_sessions` | 无 | low | `SerialSessionManager` 会话列表 |
| `list_serial_ports` | 无 | low | 枚举 COM 口 |
| `send_serial_hex` | `session_id`, `hex` | high | HEX 发送（须确认） |
| `send_serial_to_session` | `session_id`, `text` | high | 向**指定**会话发送（当前仅活动会话） |
| `set_active_serial_session` | `session_id` | medium | 切换活动会话 |

**实施进度（P4 串口扩展）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `list_serial_sessions` | ⬜ 未开始 | `handlers/serial.py` | 读类 |
| `list_serial_ports` | ⬜ 未开始 | `handlers/serial.py` | 读类 |
| `send_serial_hex` | ⬜ 未开始 | `handlers/serial.py` | 写类，需确认 |
| `send_serial_to_session` | ⬜ 未开始 | `handlers/serial.py` | 写类，需确认 |
| `set_active_serial_session` | ⬜ 未开始 | `handlers/serial.py` | medium |

### 5.6 P5 · 测试编排进阶（category=test_config / test_sequence）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `get_current_test_config` | 无 | low | 当前页面/custom_test 配置快照 |
| `apply_test_config_draft` | `draft_id` | high | 把 `generate_draft` 草案经**预览确认**后应用 |
| `list_test_steps` | 无 | low | custom_test 节点列表 |
| `run_single_step` | `step_id` | high | 单步执行（调试用） |
| `set_test_variable` | `name`, `value` | high | 设置测试变量/参数 |
| `get_test_result_summary` | 无 | low | 最近一次测试结果摘要 |

> 与 `AIService.generate_draft(kind, user_text)` 打通：模型生成草案 → `draft_ready` 信号 → UI 预览（config_preview / script_preview）→ 用户确认 → `apply_test_config_draft` 落地。草案绝不自动应用。

**实施进度（P5 测试编排）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `get_current_test_config` | ⬜ 未开始 | `handlers/test.py` | 读类 |
| `apply_test_config_draft` | ⬜ 未开始 | `handlers/test.py` | 写类，需预览确认 |
| `list_test_steps` | ⬜ 未开始 | `handlers/test.py` | 读类 |
| `run_single_step` | ⬜ 未开始 | `handlers/test.py` | 写类，需确认 |
| `set_test_variable` | ⬜ 未开始 | `handlers/test.py` | 写类，需确认 |
| `get_test_result_summary` | ⬜ 未开始 | `handlers/test.py` | 读类 |

### 5.7 P6 · 数据导出与产物（新增 category=export）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `save_scope_screenshot` | `session_id`, `dir` | medium | 把 `capture_screen_png` 存盘，回灌路径 |
| `export_datalog_csv` | `session_id`, `dir` | medium | N6705C Datalog CSV 导出 |
| `export_waveform_csv` | `label`, `t0`, `t1`, `dir` | low | 当前波形片段导出 |
| `get_artifact_list` | 无 | low | 列出本次会话产生的产物路径 |

> 产物路径限定在 `user_data/` 或用户指定目录下，禁止任意路径写入；二进制产物只回灌「路径 + 元信息」，不回灌内容本身。

**实施进度（P6 数据导出）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `save_scope_screenshot` | ⬜ 未开始 | `handlers/export.py`（新建） | 存盘，回灌路径 |
| `export_datalog_csv` | ⬜ 未开始 | `handlers/export.py` | medium |
| `export_waveform_csv` | ⬜ 未开始 | `handlers/export.py` | 读类 |
| `get_artifact_list` | ⬜ 未开始 | `handlers/export.py` | 读类 |

### 5.8 P7 · 诊断与自检（category=query / diagnostic）

| 规划动作 | 参数 | 风险 | 落地到 |
|---|---|---|---|
| `get_instrument_errors` | `session_id` | low | 驱动 `get_errors`（SCPI 错误队列） |
| `run_instrument_selftest` | `session_id` | medium | 驱动 `self_test`（`*TST?`） |
| `ping_instrument` | `session_id` | low | 驱动 `ping` / `*IDN?` |
| `get_recent_audit_log` | `lines` | low | `AuditLog` 回看 AI 历史动作 |
| `get_app_log_errors` | `lines` | low | log_ring 仅过滤 ERROR/WARN |

**实施进度（P7 诊断自检）**

| 动作 | 状态 | 负责模块 | 备注 |
|---|---|---|---|
| `get_instrument_errors` | ⬜ 未开始 | `handlers/query.py` | 读类 |
| `run_instrument_selftest` | ⬜ 未开始 | `handlers/query.py` | medium |
| `ping_instrument` | ⬜ 未开始 | `handlers/query.py` | 读类 |
| `get_recent_audit_log` | ⬜ 未开始 | `handlers/query.py` | 读类 |
| `get_app_log_errors` | ⬜ 未开始 | `handlers/query.py` | 读类 |

> 状态图例：⬜ 未开始 ｜ 🟡 进行中 ｜ ✅ 已完成 ｜ ⏸ 暂缓。实现某动作后将对应行状态更新即可，便于追踪整体落地进度。

---

## 6. 实施约束（扩展时必须遵守）

1. **注册即落地**：新动作在对应 `handlers/*.py` 的 `SPECS` 注册 + `build_handlers` 实现，并由 [builder.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/actions/builder.py) 的 `_HANDLER_MODULES` 纳入；新增 category 时同步 [registry.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/actions/registry.py) 的 `CATEGORY_*` 常量。
2. **依赖经注入**：新能力的访问器/回调一律加到 [ActionDeps](file:///d:/CodeProject/TRAE_Projects/KK_Lab/core/ai/actions/handlers/deps.py)，由 UI（MainWindow）注入，core 不反向依赖 ui；仪器一律经 `InstrumentManager`，禁止直连 `instruments/`。
3. **风险与确认**：写真机/改环境/发数据 = high + `require_confirmation=True`；只读 = low；连接/断开/切换 = medium。critical 默认禁止。
4. **写类持租约**：所有写真机动作复用 `_run_write_action` 骨架（会话已连接 + 未占用 + `try_set_busy` 租约 + finally 释放），驱动内部硬熔断不可绕过。
5. **长耗时走 worker**：`chamber_wait_stable`、`scan_instruments`、`export_*` 等异步/长流程必须 QThread，UI 不阻塞，结果经信号/轮询回灌。
6. **回灌防膨胀**：大结果（日志/CSV/截图）只回灌摘要 + 路径，经 `context_budget.clip_context_block` 裁剪。
7. **同步矩阵**：新增动作后按 [08_CHECKLISTS](file:///d:/CodeProject/TRAE_Projects/KK_Lab/docs/ai/08_CHECKLISTS.md) 核对；新增依赖更新 `requirements.txt`；模块版本动 `core/ai/__init__.py` 的 `MODULE_VERSION`。

---

## 7. 扩展后规模预估

- 现状：5 类 31 个动作（P1 连接管理 5 + 仪器测量 6 已落地）。
- 剩余规划：示波器 11 + 温箱 6 + 串口扩展 5 + 测试编排 6 + 导出 4 + 诊断 5 ≈ **37 个**。
- 全部扩展后总计约 **68 个**动作，category 由 5 类扩为 8 类（新增 `scope` / `chamber` / `export`，`diagnostic` 可并入 `query`）。
- 能力覆盖从「查询 + 基础控制」升级为「连接 → 测量 → 控制 → 编排 → 导出 → 诊断」全链路闭环。
