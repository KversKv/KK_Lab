# SerialCom 多串口架构改造规则

> 目标：在不破坏现有 `SerialComMixin` 使用方式的前提下，同时支持：
>
> 1. 单个 Serial Console 窗口内管理多个串口；
> 2. 多个窗口 / 多个页面各自拥有独立串口；
> 3. 每个串口拥有独立连接状态、接收线程、发送入口、日志归属和快捷指令目标。

---

## 1. 当前问题边界

现有 `ui/modules/serialCom_module/serialCom_module_frame.py` 的核心模型是：

```text
一个 SerialComMixin 实例 = 一个串口连接
```

关键状态都挂在当前对象上：

```python
self._serial_conn
self._serial_port
self._serial_connected
self._serial_read_thread
self._serial_read_worker
```

因此当前普通发送和快捷指令发送最终都会走：

```python
self.serial_send(data)
```

这意味着发送目标永远是当前实例的 `_serial_conn`。同一个窗口里如果要同时连接 COM1 / COM2 / COM3，不能继续只靠这一套成员变量，否则第二、第三个串口会覆盖第一个串口状态。

---

## 2. 架构原则

### 2.1 会话对象独立

必须引入独立的串口会话对象，例如：

```text
SerialSession / SerialPortSession
```

每个会话独立持有：

- `session_id`
- `display_name`
- `port`
- `baudrate`
- `bytesize / stopbits / parity / flow_control`
- `serial_conn`
- `connected`
- `read_thread`
- `read_worker`
- `rx_bytes / tx_bytes`
- `auto_baud_monitor`
- `log_panel_id` 或日志路由标识

禁止继续使用一组全局 `_serial_conn` 表示多串口。

### 2.2 UI 管理器与串口会话分离

建议拆成三层：

```text
SerialComWidget / SerialComMixin
    ↓ 只负责 UI 编排、当前选中会话、快捷指令面板、日志展示
SerialSessionManager
    ↓ 负责创建 / 删除 / 查找 / 切换多个会话
SerialSession
    ↓ 负责单个串口连接、断开、发送、接收线程生命周期
```

职责边界：

- `SerialComWidget` 不直接持有多个 `serial.Serial` 细节；
- `SerialSessionManager` 不依赖具体按钮、输入框等 Widget；
- `SerialSession` 不依赖 UI Widget，只用 Qt Signal/Slot 对外通知 RX、错误、状态变化；
- 所有串口读写仍属于 IO，必须走 Worker / QThread 或已有异步模型，不能阻塞 UI。

---

## 3. 单窗口多串口规则

单窗口多串口必须显式维护会话集合：

```python
self._sc_sessions: dict[str, SerialSession]
self._sc_active_session_id: str | None
```

推荐 UI 模型：

```text
顶部 / 侧边栏：串口 Session Tabs 或列表
每个 Session：Port、Baudrate、Connect、状态、RX/TX 计数
中间日志区：按 session_id 路由日志，可支持 All / 单串口过滤
每个 Session：独立发送输入区、发送历史、HEX/TEXT、换行、Auto Send
共享快捷指令区：默认发送到 active session，可扩展为绑定固定 session
```

### 3.1 发送区与快捷指令区决策

单窗口多串口模式下，推荐交互模型是：

```text
发送输入区：按串口独立
快捷指令区：全窗口共享
```

原因：

- 普通发送输入框应跟随串口会话独立保存，避免 COM1 / COM2 / COM3 之间输入内容、发送历史、HEX/TEXT、换行符和自动重发状态互相污染；
- 多串口调试时，独立发送区能降低误发到错误端口的风险；
- 快捷指令通常是项目级资产，不应为每个串口复制一整套按钮区，否则 UI 会膨胀且维护成本高；
- 快捷指令应提供目标选择：`Active` / 指定 session / `All`，其中 `All` 必须显式选择，禁止默认广播。

推荐布局：

```text
[Session Tabs: DUT | LOG | TOOL]

当前 Session 区域：
  Port / Baudrate / Connect / RX TX 状态
  LOG
  Send Input / Send / History / TX Format / Line Ending / Auto Send

共享 Quick Commands：
  Project / Group / Command Buttons
  Target: Active / DUT / LOG / TOOL / All
```

如果采用左右分屏或多日志面板同时展示多个串口，也仍然保持：

```text
每个串口面板拥有自己的 Send Input
底部或侧边只保留一套共享 Quick Commands
```

发送入口必须带目标：

```python
send_to_session(session_id, data) -> bool
send_to_active_session(data) -> bool
```

普通发送：

```text
Send 按钮
  -> 根据当前 active_session_id 找到 SerialSession
  -> session.send(data)
```

快捷指令：

```text
Quick Command 按钮
  -> 如果指令绑定了 target_session_id，发送到绑定会话
  -> 否则发送到当前 active_session_id
```

快捷指令数据结构建议增加可选字段：

```json
{
  "name": "reboot",
  "content": "reboot",
  "send_type": "text",
  "encoding": "ascii",
  "line_ending": "\r\n",
  "target_session_id": ""
}
```

`target_session_id` 为空时表示跟随当前选中串口，保证旧配置兼容。

---

## 4. 多窗口独立串口规则

多窗口 / 多页面场景仍然保持：

```text
一个窗口实例 = 一个独立 SerialSessionManager
```

也就是说：

- 窗口 A 的 COM1 不影响窗口 B；
- 窗口 A 的 active session 不影响窗口 B；
- 快捷指令配置可以共享，但运行时连接状态不共享；
- 不要把 `_sc_sessions` 做成类变量或全局单例；
- 串口设备本身被系统独占时，第二个窗口连接同一 COM 失败是合理行为，UI 应提示“端口被占用/连接失败”。

如果未来需要跨窗口共享串口连接，必须另立架构文档，不在本次多串口规则范围内。

---

## 5. 兼容现有 API 的过渡规则

为了不一次性改坏现有页面，保留以下兼容方法：

```python
serial_send(data)
get_serial_connection()
is_serial_connected()
close_serial()
```

但语义调整为：

```text
serial_send(data)          -> 发送到 active session
get_serial_connection()    -> 返回 active session 的 serial_conn
is_serial_connected()      -> 返回 active session 是否连接
close_serial()             -> 关闭当前窗口 / 当前控件拥有的所有 session
```

旧页面如果只创建一个串口会话，行为应与当前完全一致。

禁止让 `serial_send(data)` 隐式广播到所有串口。广播必须使用显式 API：

```python
broadcast_send(data, session_ids=None)
```

---

## 6. 信号设计

单串口会话应提供：

```python
connected_changed = Signal(str, bool)      # session_id, connected
data_received = Signal(str, bytes)         # session_id, data
error_occurred = Signal(str, str)          # session_id, message
tx_done = Signal(str, int)                 # session_id, byte_count
```

UI 层统一按 `session_id` 路由：

- 写入对应日志面板；
- 更新对应 RX/TX 计数；
- 更新对应连接状态；
- 如该 session 是 active session，同步底部状态栏。

跨线程规则：

- Worker 不直接操作 Widget；
- Worker 只 emit signal；
- UI Slot 内再更新控件。

---

## 7. 日志与快捷指令目标

日志必须带来源：

```text
[COM3][RX] ...
[COM5][TX] ...
[COM5][ERROR] ...
```

内部推荐保留结构化字段：

```python
{
    "session_id": "...",
    "port": "COM5",
    "direction": "RX",
    "payload": "...",
    "timestamp": ...
}
```

快捷指令显示层建议：

- 默认显示“发送到当前串口”；
- 如果绑定了固定串口，按钮 tooltip 显示目标；
- 当目标串口不存在或未连接时，禁止静默失败，必须写系统日志。

---

## 8. 配置持久化规则

配置建议拆为两类：

```text
user_data/SerialCom/config.json          # UI、窗口、最近会话、发送历史
user_data/SerialCom/quick_commands.json  # 快捷指令
```

多串口新增配置建议：

```json
{
  "sessions": [
    {
      "session_id": "uart1",
      "display_name": "DUT",
      "port": "COM3",
      "baudrate": 921600,
      "databit": 8,
      "stopbit": "1",
      "parity": "None",
      "flow": "None",
      "auto_detect": true
    }
  ],
  "active_session_id": "uart1"
}
```

恢复配置时：

- 可以恢复会话配置；
- 不要默认自动连接真实串口，除非用户明确开启 auto connect；
- 端口不存在时保留配置但标记不可用；
- 旧版配置没有 `sessions` 时，自动迁移为一个默认 session。

---

## 9. 改造步骤建议

### Phase 1：抽离单串口会话

- 新增 `SerialSession`，把连接、断开、读线程、发送从 `SerialComMixin` 中抽出；
- `SerialComMixin` 先只创建一个默认 session；
- 保持 `serial_send()` 等旧 API 可用；
- 跑通现有 KK Serials、Custom Test、Consumption Test、GPADC 等引用页面。

### Phase 2：引入 SessionManager

- 新增 `SerialSessionManager`；
- 支持 `create_session / remove_session / get_session / set_active_session`；
- `SerialComMixin` 的 `_serial_conn` 等旧字段改为兼容属性或仅由 active session 同步。

### Phase 3：单窗口多串口 UI

- 添加 session tab/list；
- Connect/Disconnect 作用于当前 session；
- Send/Quick 默认作用于当前 session；
- 日志按 session_id 路由，可支持过滤。

### Phase 4：快捷指令目标扩展

- Quick Command 增加可选 `target_session_id`；
- 旧配置保持空目标，表示 active session；
- 导入/导出兼容旧格式。

### Phase 5：回归与打包

- Mock 模式下验证单串口旧页面；
- Mock 模式下验证单窗口 2~3 个 session；
- 真机验证两个不同 COM 同时 RX/TX；
- 验证两个窗口分别连接不同 COM；
- 验证第二个窗口连接已占用 COM 时提示合理；
- 如新增文件或资源，按 `08_CHECKLISTS.md` 同步 `DIRECTORY_STRUCTURE.txt` / spec / helps / requirements。

---

## 10. 禁止项

- 禁止在同一个对象中继续用 `_serial_conn_2`、`_serial_conn_3` 这类平铺字段扩展；
- 禁止让多个串口共用一个 `_SerialReadWorker`；
- 禁止 Worker 直接更新 UI；
- 禁止 `serial_send(data)` 在多串口模式下悄悄广播；
- 禁止把 session 状态做成全局单例；
- 禁止在 UI 主线程执行阻塞串口读循环；
- 禁止破坏 `DEBUG_MOCK` 下的离线调试能力。

---

## 11. 推荐命名

建议新增文件：

```text
ui/modules/serialCom_module/serial_session.py
ui/modules/serialCom_module/serial_session_manager.py
```

如后续会被非 UI 业务复用，可再考虑迁移到 `core/serial/`，但迁移前必须保证：

- 不依赖 Qt Widget；
- 只使用 `QObject / Signal / QThread` 或纯 Python 回调；
- 不引入页面样式、按钮、日志控件等 UI 细节。

---

## 12. 最终判断标准

改造完成后应满足：

- 单窗口可以同时管理 COM1 / COM2 / COM3；
- Send 可以明确发送到当前选中串口；
- Quick Command 可以跟随当前串口，也可以绑定固定串口；
- 多个窗口各自维护独立连接状态；
- 旧页面只用一个串口时行为不变；
- 串口断开、关闭窗口、切换页面时线程能干净退出；
- Mock 模式可覆盖 2~3 个虚拟 session 的基本收发路径。
