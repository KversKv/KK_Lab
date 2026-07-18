# MCU IO

MCU IO 工具用于控制 **YD-RP2040** 或 **CH9114F** 这两种 USB 转GPIO 适配器，对 DUT 进行上电/复位/GPIO 电平控制。常用作 Consumption Test / VminHunter 等测试的辅助工具。

## 页面入口

- 导航栏 → `TOOLS` → `Collection` → 子菜单 `MCU IO`
- 对应源码：`ui/modules/mcu_io_module_frame.py`（`McuIoConnectionMixin`），由 `main_window.py::_CollectionPage` 包装。

## 界面布局

### 1. 顶部标题
`MCU IO (CH9114F)` 或 `MCU IO (YD-RP2040)`，随 MCU 类型切换。

### 2. 左侧连接面板（最大宽 380px）
- **MCU Type 切换**：YD-RP2040 / CH9114F。
- **Port 下拉 + 搜索按钮**：搜索可用串口。
- **Connect / Disconnect** 按钮 + 连接状态指示。
- **Baudrate**：默认 921600。

### 3. 右侧 — GPIO 控制区
- GPIO 引脚网格（YD-RP2040 全 30 引脚；CH9114F 仅 `0,1,6,7,2,8,14,20`）。
- 每个引脚一行：引脚号 + 方向（输入/输出）+ 电平按钮（High / Low / High-Z）。
- 电平按钮带 SVG 图标 + 选中颜色（High=绿 / Low=红 / HighZ=灰）。

### 4. 底部 — Execution Logs
- 标题 `MCU IO Logs`，无进度条。
- 打印每次 GPIO 设置、连接事件、错误信息。

## 典型操作流程

### 流程一：控制 DUT 上电/复位
1. 选择 MCU Type（如 CH9114F）→ 搜索 → 选择端口 → Connect。
2. 在 GPIO 网格找到 PowerOn 引脚（默认 GPIO0）→ 设方向 Output → 点击 High。
3. 找到 Reset 引脚（默认 GPIO1）→ 设方向 Output → 短暂 Low 后 High（产生复位脉冲）。

### 流程二：作为 Consumption Test 的辅助
1. 在本页连接好 MCU IO。
2. 切换到 Consumption Test → Auto Test 页面 → Control Method 选 MCU IO。
3. Consumption Test 会通过 `McuPwrResetConfigMixin` 复用本页连接，无需重复连接。

## 关键参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| MCU Type | CH9114F | YD-RP2040 / CH9114F |
| Port | — | 搜索结果选择 |
| Baudrate | 921600 | 串口波特率 |
| PowerOn GPIO | GPIO0 | 上电控制引脚 |
| Reset GPIO | GPIO1 | 复位控制引脚 |
| Status GPIO | GPIO2 | 状态回读引脚 |
| Ctrl GPIO | GPIO3 | 控制信号引脚 |

## 注意事项

- **MCU 类型差异**：
  - **YD-RP2040** 走 InstrumentManager 的 `serial_raw_repl`，引脚范围 GPIO0~GPIO29。
  - **CH9114F** 走本地 worker 连接（不共用 `serial_raw_repl`），可用引脚仅 `0,1,6,7,2,8,14,20`。
- **统一 pulse() 方法**：两种 MCU 都实现了 `pulse()` 方法用于产生脉冲（如复位信号），上层调用一致。
- **极性选项**：`Rising Edge` / `Falling Edge`，用于脉冲触发方向。
- **High-Z 状态**：将引脚设为高阻输入，避免干扰 DUT 信号。
- **状态回读**：设为 Input 方向后可读取引脚电平（High/Low）。
- **Mock 模式**：`DEBUG_MOCK=True` 时连接走 Mock，引脚状态为模拟。
- **不要硬编码端口**：端口号必须来自下拉框，禁止写入代码。
