# 通用仪器管理改善计划

> 本计划基于 [InstrumentManager_Architecture.md](./InstrumentManager_Architecture.md) 的目标架构，以及当前代码中已经引入的 `core/instruments/*`、`InstrumentManager`、`InstrumentProfile`、`InstrumentSession` 等实现。
>
> 目标不是再写一份架构设想，而是指定一条可以逐步执行、逐步验证、最终覆盖所有仪器和两种运行模式的改善路线。

---

## 1. 最终目标

改造完成后，项目必须同时满足下面这些效果。

1. `main.py` 运行时，所有页面共享同一个顶层 `InstrumentManager`。
2. 单独运行某个子页面时，页面可以创建自己的 local `InstrumentManager`，不依赖 `MainWindow`。
3. 所有仪器的搜索、连接、校验、断开都通过 `InstrumentManager + InstrumentProfile + Worker` 完成。
4. UI 层不再直接执行 VISA、串口、DLL 初始化等阻塞 IO。
5. 页面不再直接拥有仪器生命周期，只订阅 session 状态并执行业务级响应。
6. 连接成功后，不同页面可以执行自己的 post-connect 动作：
   - N6705C Analyzer 同步通道状态；
   - N6705C Datalog 重建 Active 通道；
   - Scope 页面同步型号、通道能力、截图能力；
   - VT6002 页面读取当前温度；
   - PMU / Charger / Custom Test 页面刷新可运行状态。
7. 同一个真实仪器实例只有一个 owner 负责关闭，避免重复关闭或半断开状态。
8. 长任务使用 busy / lease 机制，避免 Datalog、温箱等待、示波器长采样、eFuse 等流程互相抢占。
9. `InstrumentStatusPanel` 只从 manager snapshot 展示状态，不主动 query 真机。
10. 所有真实仪器创建统一走 `instruments/factory.py`。
11. Mock 模式下主程序和独立页面均可 smoke test。

---

## 2. 当前基线

当前已经具备的基础：

1. 已新增 `core/instruments/`：
   - `instrument_session.py`
   - `profiles.py`
   - `workers.py`
   - `registry.py`
   - `instrument_manager.py`
2. 已有 `InstrumentSession / InstrumentSnapshot / InstrumentSpec / InstrumentRequirement`。
3. 已有 `InstrumentProfile` 和默认 `ProfileRegistry`。
4. 已注册：
   - `n6705c`
   - `mso64b`
   - `dsox4034a`
   - `vt6002`
   - `keysight53230a`
5. `InstrumentManager` 已支持：
   - `connect_async`
   - `attach_external`
   - `disconnect_async`
   - `disconnect_all_async`
   - `scan_async`
   - `find_sessions`
   - `try_set_busy`
   - `shutdown`
6. `main_window.py` 已创建全局 `InstrumentManager`，并传给部分页面。
7. `n6705c_top.py` 和 `mso64b_top.py` 已经可以把 legacy top 中的外部实例 `attach_external` 到 manager。

当前仍未完善的关键缺口：

1. `InstrumentManager` 还不是单一事实源。部分页面收到 manager 后，如果 legacy top 存在，会直接忽略 manager 状态。
2. 顶层连接入口仍由 legacy top 直接创建仪器，再 `attach_external`，manager 没有真正拥有连接流程。
3. 部分页面仍在 UI 主线程执行阻塞连接或状态读取。
4. `registry.py` 的部分 `verify()` 不够严格，连接错设备时可能默认返回成功。
5. `disconnect` 仍存在 legacy top 手动改 manager session 的路径，owner 和生命周期不统一。
6. wrapper 页面接收 manager 但没有继续传给内部业务页面。
7. `InstrumentStatusPanel` 仍读取 legacy top / page 字段，甚至可能主动 query 真机。
8. busy 只有简单标志，还没有完整 lease 使用规范。
9. 串口会话和 USB-I2C 适配器尚未纳入统一 snapshot。

---

## 3. 改造总原则

### 3.1 Manager 是唯一事实源

所有页面展示和业务判断必须最终来自：

```python
manager.sessions(...)
manager.find_sessions(...)
manager.get_instance(session_id)
```

legacy top 可以短期存在，但只能作为兼容视图，不再作为事实源。

### 3.2 连接入口统一下沉

页面、top、连接面板都不能直接：

```python
N6705C(resource)
VT6002(port)
controller.connect_instrument(resource)
```

必须改成：

```python
manager.connect_async(InstrumentSpec(...))
```

如果短期必须保留旧实例注入，只能作为过渡：

```python
manager.attach_external(...)
```

且该路径应在对应阶段被移除。

### 3.3 页面负责业务反应，Manager 不知道页面业务

manager 只发出连接事实：

```text
session_connected(session_id)
sessions_changed()
connection_failed(session_id, error)
```

页面自己决定连接后做什么：

```text
Analyzer -> ChannelSyncWorker
Datalog  -> rebuild Active config
Chamber  -> ReadTemperatureWorker
Scope    -> ScopeInfoSyncWorker
```

### 3.4 IO 不进 UI 主线程

必须放入 worker 的操作：

- scan；
- connect；
- verify；
- disconnect；
- `*IDN?`；
- 通道状态同步；
- 当前温度读取；
- scope 型号和通道能力读取；
- DLL 初始化校验；
- 串口探测。

UI 主线程只更新控件和展示错误。

### 3.5 分阶段迁移，先闭环再铺开

不要同时横向改所有页面。优先把一条链路做完整：

```text
main.py -> InstrumentManager -> N6705C Top/Panel -> Analyzer/Datalog -> PMU/Charger
```

N6705C 链路跑通后，再迁移 scope、chamber、counter、serial、i2c。

---

## 4. 分阶段执行计划

## 阶段 0：冻结基线与补齐验证入口

目标：在继续改造前，先建立可重复验证的基线，避免迁移过程中不知道哪里坏了。

### 改动清单

1. 保留当前 `core/instruments/*` 结构，不再另起一套 manager。
2. 为核心模块建立最小静态验证命令：

```powershell
.venv\Scripts\python.exe -m py_compile core\instruments\instrument_session.py core\instruments\profiles.py core\instruments\workers.py core\instruments\registry.py core\instruments\instrument_manager.py
```

3. 列出每个迁移阶段必须 smoke 的页面：
   - `main.py`
   - `n6705c_analyser_ui.py`
   - `n6705c_datalog_ui.py`
   - `oscilloscope_base_ui.py`
   - `vt6002_chamber_ui.py`
   - `charger_test_ui.py`
   - `pmu_test_ui.py`
   - `custom_test_ui.py`
4. 明确 Mock 模式验证需要重启应用，因为 `DEBUG_MOCK` 是按值 import。

### 验收标准

1. 核心 manager 模块 `py_compile` 通过。
2. 当前主程序能启动到主窗口。
3. 当前 N6705C Datalog 和 Analyzer 独立入口能 import。
4. 记录当前已知失败点，后续阶段逐个清零。

---

## 阶段 1：加固核心 Manager 和 Profile

目标：先让 manager 自身可靠，避免页面迁移后把错误设备、半连接实例或线程泄漏扩散到所有页面。

### 改动清单

1. 在 `InstrumentManager` 增加 `session_changed = Signal(str)`。
2. 所有单 session 变化同时发：

```python
session_changed.emit(session_id)
sessions_changed.emit()
```

3. `disconnect_async()` 不只提前把 session 标记为 disconnected，还要在 worker 完成后发出明确的 disconnect 完成结果。
4. `shutdown()` 中避免只 `thread.quit()` 正在连接的 worker，却不要求 profile 关闭半连接实例。
5. `remove_session()` 中的同步断开改为异步或明确仅供测试/清理使用，避免 UI 调用时阻塞。
6. `ConnectWorker` 失败时关闭半连接实例时应记录 warning，不能静默吞掉断开异常。
7. `InstrumentSnapshot` 补齐 `busy_owner`，状态面板和错误提示需要知道谁占用了仪器。
8. `InstrumentSession` 增加 `updated_at` 或 `last_seen_at` 可选字段，便于状态面板显示最近变化。
9. `ProfileRegistry` 提供按 role / capability 查找 profile 的辅助方法，减少页面硬编码类型。

### Profile 校验要求

`verify()` 必须严格校验真实身份。不能因为 query 失败就返回默认型号。

1. `n6705c`：
   - 必须能拿到 IDN；
   - IDN 中必须包含 `N6705C` 或项目认可的兼容型号；
   - 否则 raise。
2. `mso64b`：
   - 必须能拿到 IDN；
   - IDN 中必须包含 `MSO64B` 或 `MSO6`；
   - 否则 raise。
3. `dsox4034a`：
   - 必须能拿到 IDN；
   - IDN 中必须包含 `DSOX4034A` 或 `DSO-X 4034A`；
   - 否则 raise。
4. `vt6002`：
   - 不能无条件成功；
   - 至少要执行一次轻量级 Modbus 读当前温度或状态寄存器；
   - 如果驱动暂不支持 probe，需要把 verify 标记为 `manual_verified`，并在 UI 明确提示这是串口候选而非已确认设备。
5. `keysight53230a`：
   - 必须能拿到 IDN；
   - IDN 中必须包含 `53230`；
   - 否则 raise。

### 验收标准

1. 选错 VISA 资源时，manager 发 `connection_failed`，不会显示 connected。
2. 连接失败后，半连接实例被关闭。
3. scan / connect / disconnect 线程结束后 `_threads` 和 `_scan_threads` 被清理。
4. Mock 模式下五类已注册 profile 均可 scan 和 connect。
5. 真机模式下错误设备不会被错误接入。

---

## 阶段 2：把 MainWindow 和状态面板改为 Manager 驱动

目标：`main.py` 中 manager 成为真正顶层仪器管理者。

### 改动清单

1. `MainWindow` 继续只创建一个全局：

```python
self.instrument_manager = InstrumentManager(parent=self)
```

2. 所有页面构造都传入同一个 `instrument_manager`。
3. `InstrumentStatusPanel` 改为只接受 manager 或 snapshots。
4. `InstrumentStatusPanel` 删除对以下对象的直接依赖：
   - `n6705c_top`
   - `mso64b_top`
   - `vt6002_chamber_ui`
5. `InstrumentStatusPanel` 禁止主动调用真实仪器方法，例如：

```python
identify_instrument()
query("*IDN?")
read_temperature()
```

6. 顶层状态刷新只响应：
   - `sessions_changed`
   - `session_changed`
   - `session_connected`
   - `session_disconnected`
   - `connection_failed`
7. `MainWindow.closeEvent` 只调用：

```python
self.instrument_manager.shutdown()
```

不要再逐个 top/page 手动断开同一批仪器。

### 验收标准

1. `main.py` 启动后，状态面板为空但正常。
2. 连接任意 manager session 后，状态面板只靠 snapshot 更新。
3. 状态刷新不会卡 UI，因为没有现场 query。
4. 关闭主窗口时不会重复 disconnect 同一个实例。

---

## 阶段 3：N6705C 链路完整 Manager 化

目标：先把最复杂、影响最大的 N6705C 共享链路做闭环。

### 3.1 N6705CTop 变成兼容视图

改造原则：

1. `N6705CTop` 不再直接创建 `N6705C`。
2. `connect_a()` / `connect_b()` 改为调用：

```python
manager.connect_async(InstrumentSpec(
    instrument_type="n6705c",
    role="power_analyzer",
    connection_kind="visa",
    slot="A" or "B",
    resource=resource,
))
```

3. `disconnect_a()` / `disconnect_b()` 改为调用：

```python
manager.disconnect_async("n6705c:A")
manager.disconnect_async("n6705c:B")
```

4. `n6705c_a / n6705c_b / is_connected_a / is_connected_b` 只从 manager snapshot 镜像出来。
5. 删除手动修改 manager session 的代码。

验收标准：

1. 从 top 连接 A/B 后，manager 中出现 `n6705c:A` / `n6705c:B`。
2. 从 manager 断开后，top 字段自动变为 disconnected。
3. top 断开不会重复关闭实例。

### 3.2 N6705C 连接面板只做 UI

改造原则：

1. 搜索按钮调用 `manager.scan_async("n6705c")`。
2. 连接按钮调用 `manager.connect_async(...)`。
3. 断开按钮调用 `manager.disconnect_async(session_id)`。
4. 连接面板不再持有真实 `self.n6705c` 作为 owner。
5. 面板可以缓存 `session_id`，但不能缓存为唯一事实源。

验收标准：

1. 搜索过程中 UI 不冻结。
2. 连接过程中 UI 不冻结。
3. 连接失败按钮能恢复。
4. 连接成功后所有订阅页面收到更新。

### 3.3 Analyzer 页面

改造原则：

1. `N6705CAnalyserUI` 构造时：

```python
self._instrument_manager = instrument_manager or InstrumentManager(parent=self)
self._owns_instrument_manager = instrument_manager is None
```

2. 即使传入 `n6705c_top`，页面也必须优先响应 manager。
3. 删除 `if self._top: return` 这类使 manager 失效的逻辑。
4. `_connect()` 不再同步创建 `N6705C` 和执行 `*IDN?`。
5. 连接成功后启动 `ChannelSyncWorker`：
   - 读取 output on/off；
   - 读取 mode；
   - 读取电压；
   - 读取电流；
   - 读取电流限制；
   - emit 结果到 UI。
6. Channel sync 失败不应断开仪器，只提示通道状态同步失败。
7. 独立运行页面时 local manager 负责连接和关闭。

验收标准：

1. `main.py` 已连接 N6705C 后，切到 Analyzer 可直接看到设备。
2. Analyzer 独立运行时能搜索、连接、同步通道。
3. 通道同步期间 UI 不冻结。
4. 通道同步失败有日志和 UI 提示，但 session 仍保持连接。

### 3.4 Datalog 页面

改造原则：

1. `N6705CDatalogUI` 同样优先响应 manager。
2. 删除 `if self._top: return` 造成的 manager 状态忽略。
3. Active 通道配置只从 connected N6705C snapshot 构建。
4. 当前仅支持 A/B 两台时，`_find_next_free_slot()` 只能返回 A/B。
5. 连接成功或断开后必须强制刷新 Active 通道配置。
6. Datalog 开始采集前必须对相关 session 设置 busy：

```python
manager.try_set_busy(session_id, True, owner="N6705CDatalogUI")
```

7. Datalog 完成、失败、用户停止时必须释放 busy。

验收标准：

1. `main.py` 中连接 N6705C 后，Datalog Active 正确显示通道。
2. 独立运行 Datalog 连接后，Active 正确显示通道。
3. 断开 A 或 B 后，对应 Active 通道移除。
4. Datalog busy 时，Analyzer 的高风险写操作被禁止或提示占用。

### 3.5 PMU / Charger / Consumption / Custom Test

改造原则：

1. wrapper 页面必须把 `instrument_manager` 继续传给内部子页面。
2. 子页面通过 requirement 查找仪器：

```python
manager.find_sessions(
    role="power_analyzer",
    required_capabilities={"set_voltage", "measure_current"},
)
```

3. core test worker 接收明确的 instrument instance 或 session_id，不直接找 legacy top。
4. 长测试开始时设置 busy，结束时释放。

验收标准：

1. `main.py` 顶层连接 N6705C 后，PMU 和 Charger 子页面都能识别可用电源。
2. 不需要再从 `n6705c_top.n6705c_a` 取实例。
3. 长测试运行时状态面板显示 busy owner。

---

## 阶段 4：示波器链路 Manager 化

目标：MSO64B / DSOX4034A 都作为 scope role 被统一管理。

### 改动清单

1. `MSO64BTop` 改成兼容视图，不再直接 owning 实例。
2. 示波器连接面板调用：

```python
manager.scan_async("mso64b")
manager.scan_async("dsox4034a")
```

或提供 scope scan 聚合入口。

3. 自动识别型号时由 profile scan / verify 决定具体 `instrument_type`。
4. `oscilloscope_base_ui.py` 中的同步连接路径改成 manager worker，不在 UI 线程调用 `controller.connect_instrument(resource)`。
5. `OscilloscopeController` 只接收已连接 instance，不负责 UI 连接流程。
6. 截图、长采样、频率测量等流程使用 busy。
7. scope 页面根据 capability 判断功能按钮是否可用。

### 验收标准

1. 连接 MSO64B 后，manager 中出现 `mso64b:main_scope`。
2. 连接 DSOX4034A 后，manager 中出现 `dsox4034a:main_scope`。
3. 状态面板能显示具体型号和 serial。
4. 截图和测量不因 manager 改造回归。
5. 错误连接到非示波器资源时连接失败。

---

## 阶段 5：温箱和频率计 Manager 化

目标：把非电源、非示波器的常规仪器也纳入统一管理。

### VT6002 改造

1. `vt6002_chamber_ui.py` 不再直接 `VT6002(device_port)`。
2. 串口枚举走 `manager.scan_async("vt6002")`。
3. 连接走 `manager.connect_async(...)`。
4. 连接成功后启动 `ReadTemperatureWorker` 读取当前温度。
5. 温度稳定等待流程设置 busy。
6. 断开走 `manager.disconnect_async("vt6002:chamber")`。

验收标准：

1. 独立运行温箱页面可用 local manager。
2. `main.py` 中温箱连接后 PMU 温扫、Charger 温扫页面可共享。
3. 读取当前温度不阻塞 UI。

### Keysight 53230A 改造

1. 频率计连接模块使用 `manager.scan_async("keysight53230a")`。
2. CLK Test 等页面通过 capability `measure_frequency` 查找 counter。
3. 频率测量长流程使用 busy。

验收标准：

1. Mock 模式可连接频率计并被 CLK Test 识别。
2. 真机错误资源不会被 verify 成功。

---

## 阶段 6：SerialCom 和 USB-I2C 纳入统一状态

目标：把“不是传统仪器但会被多个流程依赖”的连接资源纳入统一 snapshot。

### SerialCom

1. 保留 `SerialSessionManager` 管理串口 RX/TX 线程。
2. 每个串口连接向 `InstrumentManager` 暴露一个 session：

```text
serial_port:COM6
serial_port:uart_log_1
```

3. `InstrumentManager` 只展示状态和 busy，不直接接管每个字节的 RX/TX。
4. 自动波特率识别期间设置 busy。
5. 断开时由单一 owner 关闭串口线程。

验收标准：

1. SerialCom 打开的串口能显示在状态面板。
2. 串口断开后状态面板同步移除或标记 disconnected。
3. 串口自动识别期间不会被其它流程抢占。

### USB-I2C / DLL adapter

1. 新增 `usb_i2c` 或更具体的 `bes_usb_i2c` profile。
2. profile create 负责 DLL 初始化和 adapter 创建。
3. profile verify 负责环境检查：
   - DLL 是否可加载；
   - adapter 是否可访问；
   - 必要时读取一个安全寄存器或执行 no-op probe。
4. PMU / Charger / Custom Test 通过 capability 查找：
   - `read_register`
   - `write_register`
   - `efuse`
5. eFuse / 下载 / 大批量寄存器操作必须设置 busy。

验收标准：

1. DLL 缺失时连接失败并给出可读错误。
2. Mock 模式下 PMU / Charger 流程仍可运行。
3. 状态面板能显示 USB-I2C adapter 状态。

---

## 阶段 7：删除 Legacy Owner 路径

目标：完成真正的架构收敛，减少双事实源。

### 删除或降级的路径

1. 删除页面内直接 new 仪器的连接路径。
2. 删除 legacy top 手动修改 manager session 的代码。
3. 删除页面中绕开 manager 的 `is_connected_xxx` 判定。
4. `attach_external()` 只保留给测试、临时兼容或外部注入，不作为主流程。
5. 如果 `N6705CTop` / `MSO64BTop` 已无必要，标记 deprecated 或合并为通用 `InstrumentConnectionPanel`。

### 验收标准

1. 搜索 `attach_external(`，主业务路径不再命中。
2. 搜索 `N6705C(`、`VT6002(`、`connect_instrument(resource)`，UI 页面不再直接连接仪器。
3. 搜索 `identify_instrument()`，状态展示层不再主动调用。
4. 所有页面获取仪器都通过 manager。

---

## 5. 文件级改造清单

### 核心层

| 文件 | 目标 |
|---|---|
| `core/instruments/instrument_session.py` | 补齐 snapshot 字段、busy owner、时间戳、requirement 语义 |
| `core/instruments/profiles.py` | 明确 profile create / verify / scan / disconnect 契约 |
| `core/instruments/workers.py` | 加强失败清理和日志，保证 worker 不操作 UI |
| `core/instruments/registry.py` | 严格 verify；补 serial / usb_i2c profile |
| `core/instruments/instrument_manager.py` | 单 session signal、disconnect 完成回调、lease、shutdown 安全性 |
| `instruments/factory.py` | 保证所有 profile create 都走统一工厂入口 |

### UI 顶层

| 文件 | 目标 |
|---|---|
| `ui/main_window.py` | 只创建并分发一个全局 manager；关闭时统一 shutdown |
| `ui/instrument_status.py` | 只读 manager snapshots，不 query 真机 |

### N6705C

| 文件 | 目标 |
|---|---|
| `ui/pages/n6705c_power_analyzer/n6705c_top.py` | 降级为 manager-backed 兼容视图 |
| `ui/modules/n6705c_module_frame.py` | 连接控件只调用 manager，不 owning 仪器 |
| `ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py` | manager 优先；连接后异步同步通道 |
| `ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py` | manager 优先；Active 从 snapshot 构建；采集 busy |

### 示波器

| 文件 | 目标 |
|---|---|
| `ui/pages/oscilloscope/mso64b_top.py` | 降级为 manager-backed 兼容视图 |
| `ui/modules/oscilloscope_module_frame.py` | 连接控件只调用 manager |
| `ui/pages/oscilloscope/oscilloscope_base_ui.py` | 连接和识别异步化；controller 接收 instance |

### 温箱 / 频率计

| 文件 | 目标 |
|---|---|
| `ui/pages/chamber/vt6002_chamber_ui.py` | manager-backed 串口连接；读取温度异步化 |
| `ui/modules/keysight_53230a_module_frame.py` | manager-backed 频率计连接 |

### 测试流程 wrapper

| 文件 | 目标 |
|---|---|
| `ui/pages/charger_test/charger_test_ui.py` | 继续向内部子页面传递 manager |
| `ui/pages/pmu_test/pmu_test_ui.py` | 继续向内部子页面传递 manager |
| `ui/pages/consumption_test/consumption_test_wrapper.py` | 内部页面通过 manager 获取 power analyzer |
| `ui/pages/custom_test/custom_test_ui.py` | 节点运行上下文通过 manager 获取仪器 |

---

## 6. 统一接口规范

### 页面构造规范

所有需要仪器的页面统一采用：

```python
def __init__(self, instrument_manager=None, parent=None):
    super().__init__(parent)
    self._instrument_manager = instrument_manager or InstrumentManager(parent=self)
    self._owns_instrument_manager = instrument_manager is None
```

如果为了兼容暂时保留 legacy top 参数，规则是：

```python
def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
    ...
```

但页面内部事实源顺序必须是：

```text
instrument_manager -> legacy top mirror -> local fallback
```

不能因为传了 top 就忽略 manager。

### 页面关闭规范

```python
def closeEvent(self, event):
    if self._owns_instrument_manager:
        self._instrument_manager.shutdown()
    super().closeEvent(event)
```

全局 manager 由 `MainWindow` 关闭，页面不得关闭全局 manager。

### 连接请求规范

```python
spec = InstrumentSpec(
    instrument_type="n6705c",
    role="power_analyzer",
    connection_kind="visa",
    slot="A",
    resource=resource,
)
session_id = self._instrument_manager.connect_async(spec)
```

### 获取仪器规范

```python
sessions = self._instrument_manager.find_sessions(
    role="power_analyzer",
    required_capabilities={"measure_current"},
)
```

确实需要具体 instance 时：

```python
instance = self._instrument_manager.get_instance(session_id)
```

### Busy 使用规范

```python
owner = self.__class__.__name__
if not self._instrument_manager.try_set_busy(session_id, True, owner=owner):
    self._show_user_message("Instrument is busy")
    return

try:
    self._start_worker(...)
finally:
    self._instrument_manager.try_set_busy(session_id, False, owner=owner)
```

后续可升级为 context-manager lease。

---

## 7. 验收矩阵

### 主程序共享场景

| 场景 | 预期 |
|---|---|
| `main.py` 连接 N6705C A | Analyzer / Datalog / PMU / Charger 都能看到 A |
| `main.py` 连接 N6705C B | Datalog Active 同时显示 A/B 通道 |
| 断开 N6705C A | 所有页面移除 A，B 不受影响 |
| 连接 MSO64B | Scope 页面和 PMU Is Gain 页面可识别 scope |
| 连接 VT6002 | Chamber 页面和温扫流程可共享温箱 |
| 连接 53230A | CLK / 频率相关页面可识别 counter |
| 打开 SerialCom 串口 | 状态面板显示串口 session |
| 初始化 USB-I2C | PMU / Charger / Custom Test 可获取 I2C capability |

### 独立页面场景

| 页面 | 预期 |
|---|---|
| `n6705c_analyser_ui.py` | local manager 搜索、连接、同步通道 |
| `n6705c_datalog_ui.py` | local manager 搜索、连接、Active 显示通道 |
| `oscilloscope_base_ui.py` | local manager 连接 scope，不阻塞 UI |
| `vt6002_chamber_ui.py` | local manager 枚举串口、连接、读温度 |
| 频率计模块 demo | local manager 搜索、连接、测量入口可用 |

### 错误场景

| 场景 | 预期 |
|---|---|
| 选择错误 VISA 资源连接 N6705C | `connection_failed`，UI 恢复按钮 |
| 连接过程中拔掉设备 | worker 捕获异常，半连接关闭 |
| scan 过程中无 VISA backend | `scan_failed` 或空列表，可读日志 |
| 温箱串口不可用 | 连接失败，不进入 connected |
| DLL 缺失 | USB-I2C profile 连接失败并提示 DLL 路径问题 |
| Datalog 占用 N6705C 时 Analyzer 写输出 | 被 busy 拒绝或明确提示 |

---

## 8. 回归命令

### 静态编译

```powershell
.venv\Scripts\python.exe -m py_compile core\instruments\instrument_session.py core\instruments\profiles.py core\instruments\workers.py core\instruments\registry.py core\instruments\instrument_manager.py
```

迁移阶段涉及页面时追加对应页面：

```powershell
.venv\Scripts\python.exe -m py_compile ui\main_window.py ui\instrument_status.py ui\pages\n6705c_power_analyzer\n6705c_top.py ui\pages\n6705c_power_analyzer\n6705c_analyser_ui.py ui\pages\n6705c_power_analyzer\n6705c_datalog_ui.py
```

### Mock smoke

1. 设置 `debug_config.DEBUG_MOCK = True`。
2. 重启应用。
3. 运行：

```powershell
.venv\Scripts\python.exe main.py
```

4. 逐页验证：
   - scan；
   - connect；
   - status panel；
   - page sync；
   - busy；
   - disconnect；
   - close app。

### 真机 smoke

真机验证按仪器逐步执行：

1. N6705C A/B；
2. MSO64B 或 DSOX4034A；
3. VT6002；
4. Keysight 53230A；
5. SerialCom；
6. USB-I2C。

每次只接入一个仪器类型，先确认 manager 状态正确，再验证关联页面。

---

## 9. 风险与控制

### 风险 1：双事实源导致 UI 状态不一致

控制：

1. 阶段 3 起，N6705C 页面必须 manager 优先。
2. legacy top 只镜像 manager，不再主动维护最终状态。
3. 每改一个页面，删除或降级 `_sync_from_top()` 的权威地位。

### 风险 2：连接失败后半连接实例泄漏

控制：

1. `ConnectWorker` 失败路径必须调用 profile.disconnect。
2. 失败 disconnect 也要 warning 日志。
3. manager 不把失败 session 标记为 connected。

### 风险 3：UI 卡死回归

控制：

1. 搜索 `query("*IDN?")`、`identify_instrument()`、`VT6002(`、`N6705C(`。
2. 命中 UI 文件时必须迁移到 worker。
3. 状态面板禁止真机 IO。

### 风险 4：长任务抢占同一仪器

控制：

1. 先使用 `try_set_busy`。
2. 所有长任务 finally 释放 busy。
3. 后续实现 `InstrumentLease`，减少忘记释放的问题。

### 风险 5：一次性横向改太多

控制：

1. 严格按阶段推进。
2. 每阶段只迁移一条仪器链路。
3. 每阶段都能独立 py_compile 和 Mock smoke。

---

## 10. 建议执行顺序

推荐实际开发按下面顺序开 PR / commit：

1. `core/instruments` 加固：
   - strict verify；
   - session_changed；
   - better disconnect lifecycle；
   - snapshot 补字段。
2. `InstrumentStatusPanel` manager-backed。
3. `N6705CTop` manager-backed。
4. `N6705CAnalyserUI` manager-backed + ChannelSyncWorker。
5. `N6705CDatalogUI` manager-backed + Active refresh + busy。
6. PMU / Charger / Consumption / Custom Test 继续传递 manager。
7. Scope manager-backed。
8. VT6002 manager-backed。
9. Keysight 53230A manager-backed。
10. SerialCom snapshot 接入。
11. USB-I2C profile 接入。
12. 删除 legacy owner 路径。

每一步完成后都要运行对应 `py_compile`，并至少做 Mock smoke。

---

## 11. 完成定义

当下面搜索结果全部满足时，可以认为仪器管理改造完成：

1. UI 页面中没有直接创建真实仪器：

```powershell
rg -n "N6705C\\(|VT6002\\(|Keysight53230A\\(|connect_instrument\\(" ui
```

命中必须是 mock、类型注解、兼容注释或已经迁移后的非连接路径。

2. 主业务路径不再使用 `attach_external`：

```powershell
rg -n "attach_external\\(" ui core
```

命中只能是测试、临时兼容层或明确 deprecated 路径。

3. 状态面板不执行真机 IO：

```powershell
rg -n "identify_instrument|query\\(\"\\*IDN\\?\"\\)|read_temperature" ui\\instrument_status.py
```

应无命中。

4. 所有 profile verify 都会在设备不匹配时 raise。
5. 所有长任务都能标记并释放 busy。
6. `main.py` 共享场景和独立页面场景都通过 Mock smoke。
7. 至少完成 N6705C、Scope、VT6002 三类真机 smoke。

---

## 12. 不在本计划内的事项

这些事项不应混入本轮仪器管理改造，避免扩大风险：

1. 重写具体仪器驱动的 SCPI 命令集。
2. 重做 UI 视觉样式。
3. 改变测试算法或结果文件格式。
4. 重构 pyqtgraph 绘图组件。
5. 调整 PyInstaller 打包结构，除非新增运行时资源。
6. 删除 legacy top 文件，除非对应链路已经完全 manager-backed 并通过回归。
