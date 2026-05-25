# 仪器管理重构未完成项与修复计划

> 本文用于承接 [InstrumentsManagePlan.md](./InstrumentsManagePlan.md) 的实际落地检查结果。
>
> 当前代码已经做了一些 manager 兼容接入，但主要还是“页面 / 模块先连接仪器，再 `attach_external()` 登记到 manager”。这不是最终目标。后续修复必须把连接 owner 收敛到 `InstrumentManager.connect_async()`。

---

## 1. 当前完成度判断

### 总体完成度

按完整计划评估，当前完成度约为 **25%**。

已完成或基本完成：

1. `core/instruments` 基础模型已存在。
2. `InstrumentManager` 已有 session、scan、connect、disconnect、busy 的基础接口。
3. `registry.py` 的部分 verify 已比初版严格。
4. `InstrumentStatusPanel` 已基本改成从 manager snapshot 展示状态。
5. 部分 UI 模块开始接收 `instrument_manager` 参数。
6. `cleanup_mixin.py` 开始减少重复关闭仪器的逻辑。

未完成的核心目标：

1. manager 还不是唯一 owner。
2. 连接路径仍大量在 UI / module 层直接创建真实仪器。
3. `attach_external()` 被当作主流程使用。
4. 部分断开路径仍手动修改 manager session。
5. N6705C 主链路未闭环。
6. Scope、VT6002、53230A 只是兼容登记，没有真正 manager-owned。
7. PMU / Charger / Consumption / Custom Test 仍主要依赖 legacy top。
8. busy / lease 只有接口，长任务尚未接入。
9. SerialCom 和 USB-I2C 尚未纳入统一 snapshot。

---

## 2. 必须纠正的方向

### 2.1 禁止继续扩大 attach_external 主流程

`attach_external()` 只能作为临时兼容入口，用于：

1. 老代码尚未迁移时短期桥接；
2. 测试中注入已有 mock / fake instance；
3. 外部系统确实已经拥有实例生命周期。

后续新改造不能再采用：

```python
inst = N6705C(resource)
manager.attach_external(spec, inst)
```

必须改成：

```python
manager.connect_async(InstrumentSpec(...))
```

连接成功后，页面只响应：

```python
session_connected(session_id)
sessions_changed()
session_changed(session_id)
```

### 2.2 UI / module 层禁止直接连接真实仪器

后续所有连接按钮、搜索结果卡片、页面独立运行入口，都不能直接执行：

```python
N6705C(...)
VT6002(...)
MSO64B(...)
Keysight53230A(...)
controller.connect_instrument(...)
instr.query("*IDN?")
```

这些操作必须由 manager worker 或 profile worker 执行。

### 2.3 断开必须统一走 manager.disconnect_async

禁止页面直接：

```python
session.instance = None
session.connected = False
manager.sessions_changed.emit()
```

必须改成：

```python
manager.disconnect_async(session_id)
```

如果页面自己持有的是 local manager，则由 local manager 关闭；如果页面使用 global manager，则只能请求 global manager 断开。

---

## 3. 当前未完成项清单

## 3.1 核心 Manager 层

### 未完成项

1. `disconnect_finished` 当前只表示 worker finished，不区分成功 / 失败。
2. `disconnect_async()` 在 worker 完成前就把 session 标记为 disconnected，底层 close 失败时 UI 也会认为成功断开。
3. `remove_session()` 仍可能同步断开真实仪器。
4. `shutdown()` 对正在连接中的 worker 只 `quit/wait`，不能保证半连接实例被 profile.disconnect。
5. busy 只有简单标志，没有上下文管理式 lease。

### 修复计划

1. 为 `DisconnectWorker` 的成功 / 失败分别接 manager slot：
   - `_on_disconnect_finished(session_id)`
   - `_on_disconnect_failed(session_id, error)`
2. `disconnect_finished` 改成只在真正 disconnect 成功或确认无 instance 时发出。
3. 新增 `disconnect_failed = Signal(str, str)`。
4. session 可先进入 `disconnecting=True` 状态，worker 成功后再 `connected=False`。
5. `remove_session()` 改为：
   - 若 disconnected：直接移除；
   - 若 connected：调用 `disconnect_async()`，完成后移除；
   - 禁止 UI 线程同步断开。
6. 新增 `InstrumentLease` 或 `acquire/release` 包装 `try_set_busy`，保证异常时自动释放。

### 验收标准

1. disconnect 失败时状态面板能显示错误，不会误报已断开。
2. 关闭主窗口不会因正在连接中的 worker 残留导致崩溃。
3. 长任务异常退出后 busy 必定释放。

---

## 3.2 Profile / Registry 层

### 未完成项

1. 已有 profile verify 有改善，但仍需逐个真机验证。
2. VT6002 verify 依赖当前驱动能力，仍要确认 `get_current_temp()` 是否适合作为轻量 probe。
3. 尚未增加 SerialCom / USB-I2C profile。
4. scope 聚合扫描尚未定义，当前 MSO64B / DSOX4034A 仍分散。

### 修复计划

1. 给每个 profile 明确 verify 契约：
   - 成功返回 `InstrumentIdentity`；
   - 设备不匹配必须 raise；
   - 通信失败必须 raise；
   - mock 分支必须稳定返回 identity。
2. 补充 profile 单元级 smoke 脚本或最小验证入口。
3. 新增 `serial_port` profile，仅管理 session 状态和 port 生命周期。
4. 新增 `usb_i2c` 或 `bes_usb_i2c` profile，负责 DLL 初始化校验。
5. 对 scope 增加聚合扫描策略：
   - UI 可以请求 role=`scope`；
   - registry 内部分别探测 MSO64B / DSOX4034A；
   - connect 时仍落到具体 `instrument_type`。

### 验收标准

1. 错误 VISA 资源不会被任何 profile 误判成功。
2. Mock 模式下所有 profile 可 scan / connect / disconnect。
3. USB-I2C DLL 缺失时给出可读错误。

---

## 3.3 N6705C 链路

### 当前问题

N6705C 是第一优先级。当前仍存在：

1. `N6705CTop.connect_a/connect_b` 直接创建 `N6705C`。
2. `N6705CConnectionMixin` 直接创建 `N6705C` 并 query IDN。
3. `N6705CAnalyserUI._connect()` 直接创建 `N6705C` 并 query IDN。
4. `N6705CDatalogUI._ConnectWorker` 自己创建 `N6705C`，成功后 `attach_external()`。
5. Datalog/Analyzer 虽能监听 manager，但连接 owner 没收敛。
6. Datalog busy 未实际接入。

### 修复计划

#### Step 1：N6705CTop 降级为 manager-backed 兼容视图

1. `connect_a()` 改为：

```python
manager.connect_async(InstrumentSpec(
    instrument_type="n6705c",
    role="power_analyzer",
    connection_kind="visa",
    slot="A",
    resource=visa_resource,
))
```

2. `connect_b()` 同理使用 slot `B`。
3. 如果传入 `n6705c_instance`，短期允许 `attach_external()`，但必须标记为 deprecated 兼容路径。
4. `disconnect_a/b()` 只调用 `manager.disconnect_async()`。
5. `n6705c_a/b`、`is_connected_a/b`、`serial_a/b` 只由 manager signal 镜像。

#### Step 2：N6705CConnectionMixin 改为只做 UI

1. 搜索按钮调用 `manager.scan_async("n6705c")`。
2. 连接按钮调用 `manager.connect_async()`。
3. 断开按钮调用 `manager.disconnect_async("n6705c:A")`。
4. 删除直接 `N6705C(...)` 和 `instr.query("*IDN?")`。

#### Step 3：Analyzer 改为 manager-owned

1. `_connect(label)` 不再创建仪器。
2. 调用 `manager.connect_async()`。
3. 连接成功后 `_on_manager_sessions_changed()` 回填 UI。
4. 通道状态同步继续使用 `ChannelSyncWorker`，不能在 UI 线程读通道。
5. 独立运行时创建 local manager。

#### Step 4：Datalog 改为 manager-owned

1. `_on_device_connect()` 不再启动本地 `_ConnectWorker` 创建仪器。
2. 改为调用 `manager.connect_async()`。
3. `session_connected` 后根据 snapshot 建卡片 / 分配 A/B / 刷新 Active。
4. 删除主流程中的 `attach_external()`。
5. 采集开始前对所有参与 session 设置 busy。
6. 采集完成、失败、停止时释放 busy。

### 验收标准

1. 搜索 `rg -n "N6705C\\(" ui`，N6705C 主流程不再命中。
2. 搜索 `rg -n "attach_external\\(" ui/pages/n6705c_power_analyzer ui/modules/n6705c_module_frame.py`，主流程不再命中。
3. `main.py` 连接 N6705C 后，Analyzer / Datalog 均同步显示。
4. Datalog Active 在连接 / 断开 A/B 后正确刷新。
5. 连接错误资源时 UI 不冻结，且按钮恢复。

---

## 3.4 Scope 链路

### 当前问题

1. `oscilloscope_base_ui.py` 仍同步执行 `controller.connect_instrument(resource)`。
2. `oscilloscope_module_frame.py` 仍由模块 worker 创建 scope 后 `attach_external()`。
3. `MSO64BTop.connect_instrument()` 仍可能直接创建 MSO64B。
4. 断开时仍有手动修改 manager session 的代码。
5. `_on_manager_sessions_changed()` 中会直接 `instrument.identify_instrument()`，这属于 UI 线程 IO。

### 修复计划

1. Scope 页面连接按钮改为调用 manager：

```python
manager.connect_async(InstrumentSpec(
    instrument_type=selected_type,
    role="scope",
    connection_kind="visa",
    slot="main_scope",
    resource=resource,
))
```

2. 自动识别型号移到 profile scan / verify。
3. `OscilloscopeController` 改为只接收已连接 instance，不负责连接。
4. `_on_manager_sessions_changed()` 只读 snapshot，不现场 query IDN。
5. 型号、serial、title 从 `InstrumentIdentity` / snapshot 来。
6. 断开全部走 `manager.disconnect_async()`。

### 验收标准

1. UI 线程不再调用 `controller.connect_instrument(resource)`。
2. 状态同步不再调用 `identify_instrument()`。
3. MSO64B / DSOX4034A 错误资源连接失败。
4. 连接后状态面板显示具体型号。

---

## 3.5 VT6002 温箱链路

### 当前问题

1. `vt6002_chamber_ui.py` 仍直接 `VT6002(device_port)`。
2. 成功后 `attach_external()`。
3. 断开时手动改 manager session。
4. 连接和 probe 仍可能阻塞 UI。
5. 温度稳定等待未接入 busy。

### 修复计划

1. 串口扫描走 `manager.scan_async("vt6002")`。
2. 连接走 `manager.connect_async(InstrumentSpec(...))`。
3. profile verify 负责轻量读温度或状态。
4. 页面连接成功后只从 snapshot 更新 UI。
5. 断开走 `manager.disconnect_async("vt6002:default")`。
6. 温度稳定等待开始时 busy，完成/失败/停止时释放。

### 验收标准

1. UI 中不再直接 `VT6002(...)`。
2. 断开时不再手动改 session。
3. 串口错误时 UI 不冻结，session 不进入 connected。

---

## 3.6 Keysight 53230A 频率计链路

### 当前问题

1. `keysight_53230a_module_frame.py` 已接收 manager，但仍是在本地连接成功后 `attach_external()`。
2. `keysight53230a:default` 与 profile default slot `counter` 不一致，可能导致 session_id 混乱。
3. 断开已走 `disconnect_async()`，但 UI 立即调用本地 finished，可能早于真正断开完成。

### 修复计划

1. 统一 session id：建议使用 `keysight53230a:counter`。
2. 连接按钮调用 `manager.connect_async()`。
3. 连接成功后通过 `sessions_changed` 回填 `Counter_ins` 和 UI。
4. 断开 UI 等待 `disconnect_finished` 或 `session_changed` 再更新最终状态。

### 验收标准

1. 频率计主流程不再使用 `attach_external()`。
2. 状态面板和 CLK Test 能按 capability 找到 counter。
3. 错误资源不会被 verify 成功。

---

## 3.7 PMU / Charger / Consumption / Custom Test

### 当前问题

1. wrapper 接收 `instrument_manager`，但未继续传给内部页面。
2. 内部页面仍主要通过 `n6705c_top`、`mso64b_top`、`vt6002_chamber_ui` 获取仪器。
3. custom test 运行上下文仍从 legacy top 填 instrument。
4. 长测试未设置 busy。

### 修复计划

1. wrapper 创建内部页面时继续传递 `instrument_manager`。
2. 内部页面优先使用：

```python
manager.find_sessions(
    role="power_analyzer",
    required_capabilities={"measure_current"},
)
```

3. Scope 需求使用：

```python
manager.find_sessions(
    role="scope",
    required_capabilities={"measure_waveform"},
)
```

4. Chamber 需求使用：

```python
manager.find_sessions(
    role="chamber",
    required_capabilities={"set_temperature", "read_temperature"},
)
```

5. Custom Test context 从 manager snapshot / instance 构建。
6. PMU / Charger / Consumption 长任务开始前设置 busy，结束后释放。

### 验收标准

1. `main.py` 顶层连接 N6705C 后，PMU / Charger 不依赖 top 也能识别。
2. Custom Test 不再直接从 top/ref 获取仪器作为唯一来源。
3. 长任务运行时状态面板显示 busy owner。

---

## 3.8 SerialCom / USB-I2C

### 当前问题

1. SerialCom 尚未暴露到 manager snapshot。
2. USB-I2C 尚无 profile。
3. PMU / Charger / Custom Test 对 I2C 仍不是通过 manager capability 获取。

### 修复计划

1. SerialCom 每个串口连接创建一个 session：

```text
serial_port:COMx
```

2. SerialCom 自己管理 RX/TX 线程，manager 只展示状态和 busy。
3. 新增 `usb_i2c` 或 `bes_usb_i2c` profile。
4. DLL 初始化、adapter probe 放到 profile verify。
5. eFuse / 大量寄存器操作接入 busy。

### 验收标准

1. 状态面板能显示打开的串口。
2. USB-I2C DLL 缺失时 connect failed。
3. PMU / Charger 能按 capability 获取 I2C adapter。

---

## 4. 后续执行顺序

后续不要继续横向扩大兼容登记，应按下面顺序修：

1. 修 core disconnect lifecycle：
   - `disconnect_failed`
   - `disconnecting`
   - 正确的 `disconnect_finished`
2. 完成 N6705C manager-owned：
   - `N6705CTop`
   - `N6705CConnectionMixin`
   - `N6705CAnalyserUI`
   - `N6705CDatalogUI`
3. 给 Datalog 接入 busy。
4. PMU / Charger / Consumption wrapper 继续传 manager。
5. Scope manager-owned：
   - `MSO64BTop`
   - `OscilloscopeConnectionMixin`
   - `OscilloscopeBaseUI`
6. VT6002 manager-owned。
7. 53230A manager-owned。
8. Custom Test context 改为 manager 优先。
9. SerialCom snapshot 接入。
10. USB-I2C profile 接入。
11. 清理所有主流程 `attach_external()`。
12. 清理 legacy top 的 owner 能力，只保留 snapshot mirror。

---

## 5. 每阶段必跑检查

### 5.1 静态编译

涉及核心层时：

```powershell
.venv\Scripts\python.exe -m py_compile core\instruments\instrument_session.py core\instruments\profiles.py core\instruments\workers.py core\instruments\registry.py core\instruments\instrument_manager.py
```

涉及页面时追加对应文件，例如：

```powershell
.venv\Scripts\python.exe -m py_compile ui\main_window.py ui\instrument_status.py ui\pages\n6705c_power_analyzer\n6705c_top.py ui\pages\n6705c_power_analyzer\n6705c_analyser_ui.py ui\pages\n6705c_power_analyzer\n6705c_datalog_ui.py
```

### 5.2 架构搜索

每次改完必须跑：

```powershell
rg -n "N6705C\\(|VT6002\\(|Keysight53230A\\(|connect_instrument\\(" ui
rg -n "attach_external\\(" ui core
rg -n "session\\.instance\\s*=|session\\.connected\\s*=" ui
rg -n "identify_instrument\\(|query\\(\"\\*IDN\\?\"\\)|get_current_temp\\(" ui
rg -n "try_set_busy" ui core
```

命中需要逐个判定：

1. 是否在 UI 主流程；
2. 是否可以迁移到 manager worker；
3. 是否只是 mock、类型注解、demo 或驱动层测试。

### 5.3 Mock smoke

至少验证：

1. `main.py` 启动；
2. N6705C A/B 连接；
3. Analyzer 看到连接；
4. Datalog Active 显示通道；
5. Scope 连接；
6. VT6002 连接；
7. 53230A 连接；
8. 断开后状态面板同步。

---

## 6. 完成定义

只有满足下面条件，才能认为修复完成：

1. UI 主流程不再直接创建真实仪器。
2. `attach_external()` 不再出现在主业务连接路径。
3. 页面断开不再手动改 manager session。
4. N6705C、Scope、VT6002、53230A 都由 manager 发起连接。
5. Analyzer / Datalog / PMU / Charger / Custom Test 都 manager 优先。
6. 长任务全部接入 busy 或 lease。
7. 状态面板只展示 snapshot，不 query 真机。
8. main.py 共享模式和独立页面模式都通过 Mock smoke。
9. 至少 N6705C、Scope、VT6002 真机 smoke 通过。
