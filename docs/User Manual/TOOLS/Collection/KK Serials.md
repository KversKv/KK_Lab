# KK Serials

KK Serials 是**通用串口收发终端**，用于与 DUT 进行 UART 通讯，支持手动发送命令、自动接收数据、波特率切换、快速命令按钮。

## 页面入口

- 导航栏 → `TOOLS` → `Collection` → 子菜单 `KK Serials`
- 对应源码：`ui/modules/serialCom_module/serialCom_module_frame.py`（`SerialComMixin` MODE_FULL），由 `main_window.py::_KKSerialsPage` 包装。

## 界面布局

`MODE_FULL` 模式提供完整的串口终端功能：

### 1. 顶部连接区
- **Port 下拉 + 搜索按钮**：搜索可用串口。
- **Baudrate 下拉**：常用波特率（9600 / 19200 / 38400 / 57600 / 115200 / 230400 / 460800 / 921600 等）。
- **Data Bits / Stop Bits / Parity**：串口参数。
- **Connect / Disconnect** 按钮 + 连接状态指示。

### 2. 左侧 — 接收区
- 大文本区滚动显示接收到的数据（支持 hex / ASCII 切换显示）。
- 可清空、暂停接收、保存到文件。

### 3. 右侧 — 发送区
- 多行文本输入框。
- **Send 按钮**：发送当前输入框内容（支持 \\n / \\r\\n 结尾选项）。
- **快速命令按钮区**：可自定义常用命令（如 `AT+RST` / `reset` / `version`），点击即发送。
- **定时发送**：可设周期自动重发。

### 4. 底部 — 系统日志区
- `[INFO] KK Serials 已初始化` 等系统消息。
- 连接事件、错误信息、发送/接收字节数统计。

## 典型操作流程

### 流程一：基本收发
1. 选择 Port（如 COM3）+ Baudrate（如 115200）→ Connect。
2. 在发送区输入 `version` → 点击 Send。
3. 接收区显示 DUT 返回的版本信息。

### 流程二：监测 DUT 启动日志
1. 连接串口 → 暂停发送。
2. 复位 DUT（可在 MCU IO 页面操作）。
3. 接收区实时滚动 DUT 启动日志。
4. 点击 Save 保存到文件供分析。

### 流程三：快速命令
1. 在快速命令区添加常用命令按钮（如 `enter_sleep` / `wake_up`）。
2. 测试时点击对应按钮即发送，无需重复输入。

## 关键参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| Port | — | 搜索结果选择 |
| Baudrate | 115200 | 串口波特率 |
| Data Bits | 8 | 数据位 |
| Stop Bits | 1 | 停止位 |
| Parity | None | 校验位 |
| Line Ending | \r\n | 发送时追加的行尾 |

## 注意事项

- **与测试页面的串口冲突**：Consumption Test 的 SerialComMixin 是 MODE_INLINE 模式，与本页的 MODE_FULL 共享同一物理串口；同时打开会冲突，建议测试时关闭本页连接。
- **快速命令持久化**：自定义命令可保存到配置文件，下次启动自动加载（详见 `docs/ai/feature_requests/SerialCom/SerialCom_QuickCommands_UIStyle.md`）。
- **自动波特率检测**：规划中（详见 `SerialCom_AutoBaudrateDetection.md`），当前需手动设置。
- **多会话架构**：规划中（详见 `SerialCom_MultiSessionArchitecture.md`），当前仅支持单串口。
- **脚本序列**：支持脚本化批量发送（详见 `SerialCom_ScriptSequenceDesign.md`）。
- **Mock 模式**：`DEBUG_MOCK=True` 时无实际串口，但 UI 可正常显示。
- **不要硬编码端口与波特率**：必须来自下拉框。
