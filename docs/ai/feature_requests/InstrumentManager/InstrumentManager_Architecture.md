# 通用仪器管理架构方案

> 目标：为 KK_Lab 中所有实验室设备建立统一的仪器管理模型，覆盖 `main.py` 顶层共享仪器与子页面独立运行两种模式，避免每个页面、每种仪器各自维护一套连接逻辑、状态缓存和线程生命周期。

---

## 1. 当前问题

当前项目里不只有 N6705C，还包括示波器、温箱、频率计、串口设备、USB-I2C 适配器等。它们的连接协议、能力和页面使用方式不同，但都在重复处理“搜索、连接、状态同步、断开、跨页面共享”这几类问题。

现有代码大致存在几类“仪器管理”逻辑：

1. 顶层状态容器
   - 例如 `ui/pages/n6705c_power_analyzer/n6705c_top.py`；
   - 作为 `main.py` 场景下的共享状态；
   - 保存 `n6705c_a / n6705c_b / visa_resource_a / serial_a` 等具体字段；
   - 类型和 slot 写死在类里，不适合扩展到其它仪器。

2. 子页面自身逻辑
   - `n6705c_analyser_ui.py` 有自己的搜索、连接、断开、同步通道状态流程；
   - `n6705c_datalog_ui.py` 有自己的设备卡片、slot、Active 通道配置、datalog 采集流程；
   - `vt6002_chamber_ui.py`、示波器页面、PMU/Charger 页面也各自维护连接或同步逻辑；
   - 页面之间共享顶层仪器时，需要手动 `_sync_from_top()`。

3. 通用 Mixin
   - `ui/modules/n6705c_module_frame.py` 提供了 N6705C 连接控件；
   - `ui/modules/oscilloscope_module_frame.py`、`chamber_module_frame.py`、`keysight_53230a_module_frame.py` 也有类似模式；
   - 但它也直接持有 `self.n6705c / self.is_connected`；
   - 搜索与连接逻辑和页面内实现重复。

结果是：

- 顶层共享与子页面独立运行边界不清；
- 页面刷新依赖局部缓存，容易出现“连接成功但 UI 没刷新”的问题；
- 有些页面连接后需要执行额外动作，例如 Analyzer 要同步 N6705C 通道状态，示波器页面要识别型号和通道能力，温箱页面要读取当前温度；
- 连接 / 断开 / 搜索线程生命周期写法不统一，容易卡 UI；
- 未来扩展多台同类仪器、多类型仪器时会继续复制逻辑。

---

## 2. 总体原则

### 2.1 仪器实例只归一个 owner 管

任何一个真实仪器连接实例必须有唯一 owner：

```text
main.py 场景：ApplicationInstrumentManager 拥有仪器实例
子页面独立运行：页面内部 LocalInstrumentManager 拥有仪器实例
```

页面可以使用仪器，但不应该在多个地方重复关闭同一个实例。

### 2.2 页面只关心“可用会话”，不关心连接细节

页面应该拿到的是：

```text
InstrumentSession
```

而不是散落的：

```text
n6705c_a
is_connected_a
visa_resource_a
serial_a
```

页面业务只依赖：

- 当前有哪些可用仪器；
- 每台仪器的 type / role / slot / serial / resource；
- 获取仪器对象执行业务；
- 监听连接状态变化；
- 在连接后运行页面自己的同步动作。

### 2.3 仪器类型差异通过 profile/adapter 表达

不同仪器不要通过在 manager 里写一堆 `if instrument_type == ...` 扩展。每类仪器注册一个 profile：

```text
InstrumentProfile
  -> instrument_type
  -> display_name
  -> connection_kind
  -> scan_strategy
  -> create_instance
  -> verify_instance
  -> disconnect_instance
  -> capabilities
```

例如：

```text
n6705c        -> VISA / USBTMC/LAN / 多通道电源分析仪
mso64b        -> VISA / USBTMC/LAN / 示波器
dsox4034a     -> VISA / USBTMC/LAN / 示波器
vt6002        -> Serial/Modbus / 温箱
keysight53230a -> VISA / 频率计
serial_port   -> Serial / 通用串口会话
usb_i2c       -> DLL/USB / I2C 适配器
```

manager 只调用 profile，不直接知道仪器构造细节。

### 2.4 IO 永远不在 UI 主线程执行

以下操作必须走 `QObject + QThread`：

- VISA / Serial / USB-I2C 搜索；
- 打开仪器；
- `*IDN?` / Modbus 探测 / DLL 初始化校验；
- 连接后读取通道状态；
- 断开时可能阻塞的 `close()`；
- 页面启动时的设备状态同步。

UI 主线程只做：

- 更新按钮；
- 更新状态文字；
- 重建页面配置；
- 展示错误提示。

### 2.5 顶层共享和本地独立必须使用同一套接口

子页面构造时只接收一个可选 manager：

```python
class SomeInstrumentPage(QWidget):
    def __init__(self, instrument_manager=None, parent=None):
        ...
```

运行 `main.py` 时传入全局 manager。

单独运行子模块时，如果没有传入 manager，页面自己创建一个 local manager。

---

## 3. 推荐目标架构

```text
main.py
  -> MainWindow
       -> ApplicationInstrumentManager
            -> InstrumentSession[n6705c:A]
            -> InstrumentSession[n6705c:B]
            -> InstrumentSession[mso64b:main_scope]
            -> InstrumentSession[vt6002:chamber]
            -> InstrumentSession[keysight53230a:counter]
            -> InstrumentSession[serial:uart_log]
            -> InstrumentSession[usb_i2c:bes_i2c]
            -> ...

ui/pages/*
  -> PageInstrumentAdapter
       -> 订阅 manager signals
       -> 暴露页面需要的只读状态 / 操作入口

core/*
  -> 接收 instrument instance 或 session snapshot
  -> 不依赖 UI Widget

instruments/*
  -> 纯仪器驱动
  -> 不依赖 Qt Widget
```

### 3.1 新增核心对象

建议新增：

```text
core/instruments/instrument_session.py
core/instruments/instrument_manager.py
core/instruments/workers.py
core/instruments/registry.py
core/instruments/profiles.py
```

如果短期不想新建目录，也可以先放在：

```text
core/instrument_manager.py
```

后续稳定后再拆目录。

---

## 4. 数据模型

### 4.1 InstrumentSession

```python
@dataclass
class InstrumentSession:
    session_id: str              # "n6705c:A"
    instrument_type: str         # "n6705c"
    role: str                    # "power_analyzer" / "scope" / "chamber" / "counter" / "serial" / "i2c"
    slot: str                    # "A" / "B" / "main_scope" / "chamber" / "default"
    connection_kind: str         # "visa" / "serial" / "usb_i2c" / "mock"
    resource: str
    serial: str = ""
    model: str = ""
    display_name: str = ""
    capabilities: set[str] = field(default_factory=set)
    instance: object | None = None
    connected: bool = False
    owner: str = "manager"       # "manager" / "external"
    busy: bool = False
    last_error: str = ""
```

说明：

- `session_id` 是跨页面引用的稳定 key；
- `instrument_type` 是具体型号/驱动类型；
- `role` 是业务角色，例如主电源、主示波器、温箱；
- `slot` 是 UI 语义，例如 N6705C A/B、main_scope、chamber；
- `connection_kind` 用于区分 VISA、串口、USB-I2C 等底层连接；
- `capabilities` 描述能力，例如 `measure_current`、`capture_screen`、`set_temperature`；
- `instance` 是真实仪器对象；
- `owner` 用于区分“manager 创建的实例”和“外部注入的实例”；
- `busy` 用于防止同一仪器被两个长任务同时占用。

### 4.2 InstrumentSpec

用于描述连接请求：

```python
@dataclass
class InstrumentSpec:
    instrument_type: str
    role: str = ""
    connection_kind: str = ""
    resource: str
    slot: str = "default"
    serial: str = ""
    model_hint: str = ""
```

### 4.3 InstrumentSnapshot

给 UI 展示用，避免 UI 直接依赖可变 session：

```python
@dataclass(frozen=True)
class InstrumentSnapshot:
    session_id: str
    instrument_type: str
    role: str
    slot: str
    connection_kind: str
    resource: str
    serial: str
    model: str
    capabilities: frozenset[str]
    connected: bool
    busy: bool
    last_error: str
```

---

## 5. InstrumentManager 职责

### 5.1 必须提供的能力

```python
class InstrumentManager(QObject):
    sessions_changed = Signal()
    session_changed = Signal(str)
    connection_failed = Signal(str, str)  # session_id, error

    def sessions(self, instrument_type: str | None = None) -> list[InstrumentSnapshot]: ...
    def get_session(self, session_id: str) -> InstrumentSession | None: ...
    def get_instance(self, session_id: str) -> object | None: ...

    def connect_async(self, spec: InstrumentSpec) -> str: ...
    def attach_external(self, spec: InstrumentSpec, instance: object) -> str: ...
    def disconnect_async(self, session_id: str) -> None: ...
    def disconnect_all_async(self) -> None: ...

    def scan_async(self, instrument_type: str) -> None: ...
```

### 5.2 不能做的事

`InstrumentManager` 不应该：

- 创建具体页面控件；
- 弹 `QMessageBox`；
- 操作某个页面的按钮；
- 了解 Analyzer / Datalog 的业务参数；
- 直接在主线程执行 VISA IO。

### 5.3 允许做的事

`InstrumentManager` 可以：

- 维护仪器连接状态；
- 创建 / 关闭仪器实例；
- 通过 `instruments.factory` 创建仪器；
- 统一做 `DEBUG_MOCK` 分支；
- 统一发出 Qt 信号；
- 维护 session 的 busy 状态。

---

## 6. 仪器分类与能力模型

### 6.1 仪器不按页面分类，按 type + role + capability 分类

同一台仪器可能被多个页面使用，不能按页面归属。例如 N6705C 同时服务：

- DC Power Analyzer 页面；
- Datalog 页面；
- PMU 测试；
- Charger 测试；
- Custom Test 节点。

因此 manager 的分类方式应为：

```text
instrument_type: 具体驱动/型号
role: 当前业务角色
capabilities: 可执行能力
```

示例：

| instrument_type | role | connection_kind | capabilities |
|---|---|---|---|
| `n6705c` | `power_analyzer` | `visa` | `set_voltage`, `measure_current`, `datalog`, `multi_channel_output` |
| `mso64b` | `scope` | `visa` | `capture_screen`, `measure_waveform`, `auto_detect_channels` |
| `dsox4034a` | `scope` | `visa` | `capture_screen`, `measure_waveform` |
| `vt6002` | `chamber` | `serial_modbus` | `set_temperature`, `read_temperature`, `stabilize_wait` |
| `keysight53230a` | `counter` | `visa` | `measure_frequency`, `measure_period` |
| `serial_port` | `uart_log` | `serial` | `read_stream`, `write_bytes`, `auto_baud` |
| `usb_i2c` | `i2c_adapter` | `dll_usb` | `read_register`, `write_register`, `efuse` |

### 6.2 capability 用于页面依赖声明

页面不要硬编码“我必须要 N6705C”，而应声明自己需要什么能力。

例如：

```python
required = InstrumentRequirement(
    role="power_analyzer",
    capabilities={"set_voltage", "measure_current"},
)
```

Datalog 页面：

```python
required = InstrumentRequirement(
    role="power_analyzer",
    capabilities={"datalog", "measure_current"},
    min_count=1,
    max_count=2,
)
```

示波器页面：

```python
required = InstrumentRequirement(
    role="scope",
    capabilities={"capture_screen", "measure_waveform"},
)
```

这样未来如果新增其它型号电源分析仪，只要它实现相同 capability，页面就可以复用。

### 6.3 profile 负责把具体型号映射成 capability

```python
@dataclass(frozen=True)
class InstrumentProfile:
    instrument_type: str
    display_name: str
    connection_kind: str
    capabilities: frozenset[str]
    create: Callable[[InstrumentSpec], object]
    verify: Callable[[object], InstrumentIdentity]
    scan: Callable[[], list[InstrumentCandidate]]
    disconnect: Callable[[object], None]
```

`InstrumentIdentity`：

```python
@dataclass(frozen=True)
class InstrumentIdentity:
    model: str
    serial: str
    vendor: str = ""
    firmware: str = ""
```

`InstrumentCandidate`：

```python
@dataclass(frozen=True)
class InstrumentCandidate:
    instrument_type: str
    connection_kind: str
    resource: str
    model_hint: str = ""
    serial_hint: str = ""
    display_name: str = ""
```

---

## 7. 页面接入方式

### 7.1 页面构造

页面统一接受 manager，可选：

```python
class N6705CAnalyserUI(QWidget):
    def __init__(self, instrument_manager=None, parent=None):
        super().__init__(parent)
        self.instrument_manager = instrument_manager or InstrumentManager(parent=self)
        self._owns_manager = instrument_manager is None
```

规则：

- `main.py` 创建页面时传入全局 manager；
- 直接运行页面时页面创建本地 manager；
- 页面关闭时，如果 `_owns_manager=True`，页面负责断开本地 manager；
- 如果 `_owns_manager=False`，页面不能关闭全局 manager 中其他页面还在使用的仪器。

### 7.2 页面监听状态

```python
self.instrument_manager.sessions_changed.connect(self._sync_instruments_from_manager)
self.instrument_manager.session_changed.connect(self._on_instrument_session_changed)
```

页面自己实现：

```python
def _sync_instruments_from_manager(self):
    sessions = self.instrument_manager.sessions(role="power_analyzer")
    ...
```

### 7.3 页面级连接后动作

不同页面的“连接后动作”不应该塞进 manager。

推荐页面提供 hook：

```python
def _on_instrument_session_connected(self, session_id: str):
    pass
```

Analyzer：

```python
def _on_instrument_session_connected(self, session_id):
    self._start_channel_sync(session_id)
```

Datalog：

```python
def _on_instrument_session_connected(self, session_id):
    self._rebuild_active_channel_config()
```

PMU / Charger 页面：

```python
def _on_instrument_session_connected(self, session_id):
    self._update_start_button_state()
```

这样 manager 只负责“连接事实”，页面负责“业务反应”。

---

## 8. main.py 场景

### 8.1 MainWindow 持有全局 manager

```python
class MainWindow(QMainWindow):
    def __init__(self):
        ...
        self.instrument_manager = ApplicationInstrumentManager(self)
```

页面懒加载时：

```python
self.n6705c_analyser_ui = N6705CAnalyserUI(
    instrument_manager=self.instrument_manager,
    parent=self,
)
self.n6705c_datalog_ui = N6705CDatalogUI(
    instrument_manager=self.instrument_manager,
    parent=self,
)
```

### 8.2 顶层仪器状态面板

`InstrumentStatusPanel` 不再直接读 `n6705c_top.n6705c_a`。

改为：

```python
snapshots = self.instrument_manager.sessions()
```

并显示：

- type；
- slot；
- serial；
- resource；
- connected；
- busy。

### 8.3 顶层连接入口

顶层连接入口调用：

```python
manager.connect_async(InstrumentSpec(
    instrument_type="n6705c",
    role="power_analyzer",
    connection_kind="visa",
    slot="A",
    resource=resource,
))
```

连接完成后所有页面自动收到 `sessions_changed`。

---

## 9. 子页面独立运行场景

子页面底部 demo 入口保持简单：

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    w = N6705CDatalogUI(instrument_manager=manager)
    w.show()
    sys.exit(app.exec())
```

或者页面内部自动创建：

```python
w = N6705CDatalogUI()
```

两者都允许，但推荐显式创建 manager，便于调试。

独立运行时：

- 页面可以显示自己的连接面板；
- 连接面板调用本地 manager；
- 关闭窗口时断开本地 manager；
- 不依赖 `MainWindow` 或 `N6705CTop`。

---

## 10. 各类仪器特化策略

### 10.1 电源分析仪 / 电源类

当前代表：

- `n6705c`

典型能力：

- 多通道输出；
- 设置电压 / 电流 / 限流；
- 测量电压 / 电流 / 功耗；
- datalog；
- 通道状态同步。

页面连接后动作：

- Analyzer：同步通道状态、模式、电压、电流、限流；
- Datalog：重建 Active 通道配置；
- PMU / Charger：更新开始按钮和参数合法性；
- Custom Test：刷新节点运行上下文。

### 10.2 示波器类

当前代表：

- `mso64b`
- `dsox4034a`

典型能力：

- 捕获屏幕；
- 读取波形；
- 执行测量项；
- 自动识别型号 / 通道数量；
- 不同型号 SCPI 命令差异较大。

策略：

- profile 的 `verify()` 必须识别具体型号；
- `capture_screen` 等能力通过驱动统一接口暴露；
- 页面需要依赖 capability，不要直接写死 MSO64B 或 DSOX4034A；
- 型号差异留在 instruments 驱动层或 scope adapter，UI 不分支 SCPI。

### 10.3 温箱类

当前代表：

- `vt6002`

典型能力：

- 设置目标温度；
- 读取当前温度；
- 等待温度稳定；
- 串口 / Modbus RTU 通信。

策略：

- connection_kind 使用 `serial_modbus`；
- scan 可能不是自动发现，而是枚举串口 + 用户选择；
- `stabilize_wait` 属于长耗时流程，必须通过 worker；
- 温箱被测试流程占用时应设置 busy，避免其它页面改变温度。

### 10.4 频率计类

当前代表：

- `keysight53230a`

典型能力：

- 频率测量；
- 周期测量；
- VISA 连接；
- 需要型号校验。

策略：

- 作为 `counter` role；
- clk test 等页面声明 `measure_frequency` capability；
- 连接面板不直接创建实例，统一交给 manager。

### 10.5 串口设备 / 日志口

当前代表：

- `serial_port`
- SerialCom 多串口会话

典型能力：

- 持续接收日志流；
- 发送文本 / HEX；
- 自动波特率识别；
- 多 session 并存；
- 与普通仪器不同，它本身常常是“会话集合”。

策略：

- 可以纳入 InstrumentManager，但 session granularity 必须是单个串口连接；
- `session_id` 示例：`serial:COM6` 或 `serial:uart_log_1`；
- 多串口窗口内部仍可使用 `SerialSessionManager`，但它应能向全局 manager 暴露 snapshot；
- 串口 RX 线程属于 session 内部生命周期，不应被页面直接管理。

### 10.6 USB-I2C / DLL 适配器

当前代表：

- BES USB-IO I2C；
- CH341；
- eFuse / register 访问链路。

典型能力：

- 读写寄存器；
- eFuse；
- 依赖 DLL；
- 可能不能自动发现具体目标芯片。

策略：

- connection_kind 使用 `dll_usb`；
- profile 负责 DLL 初始化和环境校验；
- capability 区分 `read_register`、`write_register`、`efuse`；
- 页面和 core 只通过 adapter/driver API 调用，不直接 LoadLibrary。

---

## 11. N6705C 具体规则

### 11.1 Slot 规则

N6705C 当前业务只支持 A/B 两台：

```text
n6705c:A
n6705c:B
```

除非 datalog 采集、通道配置和结果命名都扩展到 N 台，否则不要在 UI 上提供 C/D 真实连接 slot。

如果未来要支持多台，应统一改成：

```text
n6705c:0
n6705c:1
n6705c:2
...
```

并把当前所有 `a/b` 字段改成 dict：

```python
self.n6705c_sessions: dict[str, InstrumentSession]
self.channel_widgets_by_session: dict[str, ChannelConfigWidgets]
```

### 11.2 Analyzer 连接后同步

Analyzer 的需求是连接后主动确认通道状态：

- `get_channel_state(ch)`；
- `get_mode(ch)`；
- `measure_voltage(ch)`；
- `measure_current(ch)`；
- `get_current_limit(ch)`。

这些必须放到 `ChannelSyncWorker`，不能在连接成功槽里同步读取。

推荐流程：

```text
manager session connected
  -> Analyzer._on_n6705c_session_connected(session_id)
  -> AnalyzerChannelSyncWorker(session.instance)
  -> result signal
  -> UI 更新当前通道控件
```

### 11.3 Datalog 连接后刷新

Datalog 的需求是连接后重建 Active 通道配置：

```text
manager session connected
  -> Datalog._sync_instruments_from_manager()
  -> 根据 N6705C sessions 重建 Active tab
  -> A/B 通道 checkbox 与采集列表一致
```

Active tab 不应该依赖 slot frame 的临时 property 作为唯一事实源。

推荐用 `InstrumentSnapshot` 生成：

```python
sessions = manager.sessions("n6705c")
for session in sessions:
    build_channel_config(session.session_id, session.slot, session.serial)
```

---

## 12. 连接与搜索线程

### 12.1 连接 Worker

```text
ConnectInstrumentWorker
  -> profile.create(spec)
  -> profile.verify(instance)
  -> emit connected(session data, instance)
```

失败时：

- worker 内部关闭半连接实例；
- emit error；
- manager 更新 session.last_error；
- UI 收到信号后恢复按钮。

### 12.2 搜索 Worker

不同 connection_kind 的搜索方式不同：

| connection_kind | 搜索策略 |
|---|---|
| `visa` | `pyvisa.ResourceManager().list_resources()` + profile probe |
| `serial` | 枚举 COM 口，必要时读取设备握手或用户手动确认 |
| `serial_modbus` | 枚举 COM 口 + Modbus 地址探测，或用户指定 |
| `dll_usb` | DLL 初始化 + 适配器枚举，失败时返回可读错误 |
| `mock` | 从 mock registry 返回候选项 |

manager 提供统一信号：

```python
scan_finished = Signal(str, list)  # instrument_type, candidates
scan_failed = Signal(str, str)     # instrument_type, error
```

### 12.3 线程生命周期标准写法

统一使用：

```python
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.finished.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.finished.connect(cleanup)
thread.start()
```

禁止在 UI 主线程里做无超时：

```python
thread.wait()
```

断开时如果必须等待，最多使用短超时，并优先异步断开：

```python
thread.wait(3000)
```

---

## 13. Busy / Lease 机制

多个页面共享同一台仪器时，必须避免两个长任务同时控制同一台仪器。

建议 manager 提供 lease：

```python
lease = manager.acquire(session_id, owner="N6705CDatalogUI", purpose="datalog")
if not lease:
    ...
```

`lease` 用上下文管理：

```python
with manager.acquire(session_id, owner, purpose) as inst:
    ...
```

短期可先实现简单 busy 标志：

```python
def try_set_busy(session_id, busy, owner="") -> bool
```

长任务开始：

```text
mark busy -> start worker -> finished/error -> clear busy
```

例如：

- Datalog 采集；
- 温箱温度稳定等待；
- 示波器长时间波形采集；
- 串口自动波特率扫描；
- eFuse 烧录。

Analyzer 的单次通道读取可以不锁长 busy，但写入输出、电压、电流时应检查是否已有 datalog 正在占用。

---

## 14. 与 instruments.factory 的关系

连接实例必须统一走 factory：

```python
create_power_analyzer(resource)
create_oscilloscope(type, resource)
create_chamber(port, baudrate)
create_frequency_counter(type, resource)
```

建议新增通用入口：

```python
def create_instrument(instrument_type: str, **kwargs):
    ...
```

示例：

```python
create_instrument("n6705c", resource=resource)
create_instrument("mso64b", resource=resource)
create_instrument("vt6002", port=port, baudrate=baudrate)
create_instrument("keysight53230a", resource=resource)
create_instrument("serial_port", port=port, baudrate=baudrate)
create_instrument("usb_i2c", adapter="bes_usbio")
```

这样 manager 不需要知道每种仪器的具体构造函数。

---

## 15. 迁移方案

### 阶段 1：建立通用模型，兼容当前入口

目标：不大改 UI，先把事实源统一。

1. 新增 `InstrumentSession / InstrumentManager`；
2. 新增 `InstrumentProfile / registry`；
3. 先注册 `n6705c / mso64b / dsox4034a / vt6002 / keysight53230a`；
4. 让 `N6705CTop` 临时包装 manager，保留旧字段；
5. 让现有各页面逐步从 manager 读取 snapshot。

兼容层：

```python
class N6705CTop(QObject):
    def connect_a(...):
        self.manager.attach_external(...) or self.manager.connect_async(...)
```

### 阶段 2：N6705C 页面接入 manager

目标：先修复当前最复杂的电源分析仪共享链路。

1. `N6705CConnectionMixin` 改为只负责 UI；
2. 搜索 / 连接 / 断开交给 manager；
3. PMU / Charger / Custom Test 页面通过 manager 获取 N6705C；
4. `InstrumentStatusPanel` 通过 manager 展示所有仪器。

### 阶段 3：示波器、温箱、频率计接入 manager

目标：把所有“单独 top / 单独 mixin 自管”的仪器逐步迁移。

1. 示波器 Mixin 改为 manager-backed；
2. 温箱页面改为 manager-backed；
3. 频率计连接模块改为 manager-backed；
4. 页面只声明 capability requirement。

### 阶段 4：串口 / USB-I2C 适配器接入

目标：把非 VISA 设备也纳入统一状态面板，但保留它们自己的专用 session 管理。

1. SerialCom 的 `SerialSessionManager` 向 InstrumentManager 暴露 session snapshot；
2. USB-I2C profile 负责 DLL 初始化和 adapter 状态；
3. 测试流程通过 requirement 获取 `serial` / `i2c_adapter` 能力。

---

## 16. 推荐文件结构

短期：

```text
core/
  instrument_manager.py
```

中期：

```text
core/
  instruments/
    __init__.py
    instrument_session.py
    instrument_manager.py
    workers.py
    registry.py
    profiles.py
    requirements.py
```

页面层：

```text
ui/modules/
  instrument_connection_panel.py  # 通用连接面板，只做 UI
  n6705c_connection_panel.py      # N6705C 特化显示，不 owning 仪器
  scope_connection_panel.py       # 示波器特化显示，不 owning 仪器

ui/pages/n6705c_power_analyzer/
  n6705c_analyser_ui.py           # Analyzer 页面业务
  n6705c_datalog_ui.py            # Datalog 页面业务
```

旧文件：

```text
ui/pages/n6705c_power_analyzer/n6705c_top.py
```

保留为兼容层，最终可废弃。

---

## 17. 关键接口示例

### 17.1 manager 获取 N6705C A

```python
session = manager.get_session("n6705c:A")
if not session or not session.connected:
    raise RuntimeError("N6705C A not connected")
n6705c = session.instance
```

### 17.2 manager 按 capability 查找仪器

```python
sessions = manager.find_sessions(
    role="scope",
    required_capabilities={"capture_screen"},
)
```

### 17.3 页面刷新

```python
def _sync_instruments_from_manager(self):
    sessions = self.instrument_manager.sessions(role="power_analyzer")
    self._sessions_by_slot = {s.slot: s for s in sessions if s.connected}
    self._rebuild_active_channel_config()
```

### 17.4 页面独立运行

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    win = N6705CAnalyserUI(instrument_manager=manager)
    win.show()
    sys.exit(app.exec())
```

---

## 18. 判断标准

改造完成后应满足：

- `main.py` 中连接 N6705C 后，Analyzer / Datalog / PMU / Charger 页面都能同步看到；
- `main.py` 中连接示波器、温箱、频率计、串口/I2C 适配器后，相关页面都能通过 manager 同步看到；
- 单独运行 `n6705c_analyser_ui.py` 可以独立搜索、连接、同步通道状态；
- 单独运行 `n6705c_datalog_ui.py` 可以独立搜索、连接、显示 Active 通道；
- 单独运行示波器、温箱、频率计、串口相关页面时，可以创建 local manager 并独立工作；
- 连接、搜索、断开不阻塞 UI；
- 同一台仪器不会被多个 owner 重复关闭；
- Datalog、温箱等待、示波器长采样、eFuse 等长任务期间，其它页面不能抢占同一 session 做高风险操作；
- 所有真实仪器创建都走 `instruments.factory`；
- `instruments/` 不依赖 UI；
- 页面只通过 Signal/Slot 响应 manager 状态。
