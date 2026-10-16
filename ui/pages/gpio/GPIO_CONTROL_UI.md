# BES GPIO Workbench — gpio_control_ui.py 功能说明

> 本文描述 [gpio_control_ui.py](./gpio_control_ui.py)（`GpioControlUI`）的全部功能。
> 局部约定与坑点见同目录 [AGENTS.md](./AGENTS.md)；硬件语义 / 动作构造见 `core/gpio/`。

## 1. 定位与铁律

- **职责**：DUT GPIO 控制页（TOOLS 组）——Detect DUT → Bank 管理 → 5 大视图 GPIO 操控。
- **仅真机控制**：无仿真模式；所有读写经 `core/gpio/` Worker（QThread）到 USB-I2C 硬件，页面无阻塞 I2C。
- **就绪条件 `_ready()`** = 已加载 GPIO 配置 且 `dev_addr` 已知（即必须先 `i2c.bes_chip_check()`；Load Profile / Apply Config 也依赖先 Detect）。
- **影子寄存器模型**：方向寄存器只有 set/clear 无回读地址，模式状态仅本页会话内记忆；页面以 `_dir_shadow` / `_out_shadow`（按 bank）与 `_reg_shadow`（按地址，PU/PD/drv/任意写）维护影子，引脚模式、上下拉、drv、统计全部由影子推导。

### 硬件语义（严格 SET/CLR，杜绝读-改-写竞态）

| 操作 | 寄存器偏移 | 说明 |
|---|---|---|
| HIGH | Base + 0x00（Out Set） | 写 1 生效位 |
| OUTPUT | Base + 0x04（Dir Set） | 写 1 生效位 |
| LOW | Base + 0x0C（Out Clr） | 写 1 生效位 |
| INPUT | Base + 0x10（Dir Clr） | 写 1 生效位 |
| 读输入电平 | Base + 0x50（Input Read） | 只读 |

- 每 bank 32 GPIO，`bit = (group % 4) * 8 + pin`；bank 可用 `groups` 字段声明有效 group 数（1~4，高位 group 不显示/不参与批处理与统计）。
- PU/PD/drv 为普通 RW 寄存器，必须 OP_BITS 位域写（DLL RMW），禁整写覆盖其他脚。
- 设备地址固定 BIT_32，dev 取 `chip_info["main_die_i2c_addr"]`（0x11 / 0x31 自适应）。

## 2. 页面结构总览

```
Top Bar（品牌 + DUT 副标题 / 5 大视图 Tab / Speed / i2c.bes_chip_check()）
→ DUT 状态与 Bank 面板（Profile / Bank / 地址速览 / 遥测统计 / 状态）
→ 批处理与掩码注入工具条（全组操作 / 32bit 掩码）
→ 中央主工作视口 QStackedWidget（5 大视图）
→ Activity Logs（ExecutionLogsFrame，QSplitter 竖分，stretch 5:1）
```

- 页面级 QSS 常量 `_GPIO_PAGE_QSS` 一次性 `setStyleSheet`（60-30-10 暗色精密仪器调色板）；控件高度一律 QSS `min-height == max-height` 钉死，顶栏 `#gpioTab` 例外（Expanding 垂直撑满两行高）。
- 命名约定：`GPIO{group}{pin}`（Group0→GPIO00~07）；bank 内位号 `BIT{bit:02d}`；卡片与 Inspector 以 GPIO 名为显眼主标签、BIT 位号为暗淡副标签。
- 页面 UI 文本一律英文（Label / 按钮 / ToolTip / Activity Logs）。

## 3. Top Bar

- **品牌区**：gpio-pins.svg 图标 + 标题 "BES GPIO Workbench" + `dut_sub` 副标题（`DUT: <芯片> · dev 0xXX`）。
- **5 大视图 Tab**（QButtonGroup 互斥 + QStackedWidget）：Pin Matrix / Register Map / I2C Sniffer / JSON Config / Confirm Note，hover 显示完整名称。
- **Speed 下拉**：USB-I2C 桥速度 20k / 100k（默认）/ 400k / 750k Hz（懒加载 `I2CSpeedMode`）。
- **`i2c.bes_chip_check()` 主按钮**（`#gpioPrimary`）：Detect DUT。执行期间 refresh-cw 图标每 100ms 旋转 90°（`_spin_timer`），结束后复位。
  - 成功：取 `main_die_i2c_addr` → 按 `chip_name` 加载 `chips/gpio_configs/<chip>.json` → 同步 Profile 下拉 → 复位会话状态 → 刷新全部视图 → **延迟 ≥50ms 自动全量回读**（`_defer_read(_start_read_all_banks)`）。
  - Main-die 读取失败 / 无对应 JSON 配置：状态栏报错并打日志，不进入就绪态。

## 4. DUT 状态与 Bank 面板

- **DUT Profile**：下拉列出 `chips/gpio_configs/*.json` 全部芯片预设；`Load` 手动加载选中 Profile（需先 Detect，否则警告），加载后同样复位会话 + 全量回读。
- **Bank 切换**：按配置动态生成数字方块按钮（0..N-1），ToolTip 显示 `Bank i · 名称 · GPIO_GroupX~Y · base 0x...`；切 bank 清空选中并重建 Matrix / RegMap / 统计 / Inspector。
- **地址速览**：`Base 0x........` + `Bank<i> (GPIO_GroupX~Y)`。
- **遥测统计**（6 项，由影子推导）：OUT / IN / HIGH / LOW / PU / PD 计数（HIGH/LOW 需已读过 0x50，否则 `-`；PU/PD 地址未配置显示 `-`）。
- **状态标签**：Not Detected / Detecting... / 结果摘要，`ok` 绿色 / `err` 红色。

## 5. 批处理与掩码注入工具条

6 个批处理按钮（作用于当前 bank 全部有效引脚，动作前自动 func_sel 掩码前置，完成后延迟回读本 bank 0x50）：

| 按钮 | 动作 |
|---|---|
| All OUT HIGH | DIR_SET + VAL_SET = 有效引脚掩码 |
| All OUT LOW | DIR_SET + VAL_CLR = 有效引脚掩码 |
| All IN Hi-Z | DIR_CLR = 掩码，且 PU/PD 全清 0（OP_BITS） |
| All PU / All PD | PU/PD 整 bank 位域写（先清反向拉）；地址未配置时警告不下发 |
| Invert OUT | 按影子取所有输出脚，电平反转为 HIGH↔LOW（无输出脚时提示） |

**Mask 注入**：`HexWheelLineEdit`（滚轮调值）输入 32bit 掩码 + 目标选择（VAL_SET / DIR_SET / VAL_CLR / DIR_CLR）→ `Write Mask` 整写所选 SET/CLR 寄存器（自动 func_sel 前置 + 回读 0x50）。

## 6. 视图 1：Pin Matrix

### 6.1 引脚卡片矩阵

- 当前 bank 全部有效引脚按 BIT 降序排成**两列**（左列 BIT31~16、右列 BIT15~0），行距 0 斑马纹，行间 1px 分隔线。
- 每张卡片（`_PinCard`）：`BITnn` + GPIO 名 + 别名/功能名 + `OUT/IN` 方向钮 + `H/L/0/1/-` 电平钮 + `Z/PU/PD` 上拉循环钮 + LED。
  - **方向钮**：Toggle 方向（Dir Set +0x04 / Dir Clr +0x10），写后回读 0x50。
  - **电平钮**：输出态 Toggle HIGH/LOW（Out Set +0x00 / Out Clr +0x0C）；**输入态禁用置灰**（INPUT 时 Inspector HIGH/LOW 同步禁用），输入态点击卡片电平钮改为触发本 bank 0x50 回读。
  - **pull 钮**：Hi-Z → PU → PD 循环；JSON 未配置 PU/PD 地址时禁用并提示。
  - **LED / 边框**：输出 HIGH 或读到输入高电平时点亮（青色）。
- 卡片 ToolTip：`GPIO名 · Bank名 BITnn · Global #N · Function: xxx`。

### 6.2 选中与 Ctrl 多选

- 普通点击 = 单选；**Ctrl+Click** 累加/移除（`_selected_pins` 有序列表，`_selected` = 最后点击的主选中）；卡片动作钮 / 切 bank / 会话复位均重置为单选或清空。
- 多选（≥2）时 Inspector 切换为三容器显隐：`_insp_single_box`（别名+信息，隐）/ `_insp_multi_box`（选中列表：GPIO 名 + 当前模式 + 行内移除）/ `_insp_state_box`（大字电平+mask，隐）。
- 多选统一配置：方向/电平按 `_selected_by_bank()` 聚合掩码 + func_sel 掩码前置一次 `_apply_actions`；pull/drv 逐脚动作拼接一次下发；统一 `_queue_banks_read` 回读受影响 bank。
- 多选使能规则：全体为输出才放电平钮、全体支持 pull/drv 才放对应钮；drv 混档显示 `Lv a~b`，加减档按全体同步 ±1（越界自动钳位）。

### 6.3 Inspector（右侧 300px 属性面板）

- **单选**：GPIO 大名 + `Alias` 别名编辑（会话内记忆，回车生效并回显卡片）+ 脚位信息（Bank / BIT / Group / Pin / Global # / 模式 label）。
- **Direction**：OUTPUT / INPUT 二元按钮（当前态高亮）。
- **Output Level**：HIGH / LOW（INPUT 时禁用）。
- **Pull Tri-State**：High-Z / Pull-Up / Pull-Down 三态（PU/PD 已配置阻抗时标题显示 `PU≈xx Ω / PD≈xx Ω`）。
- **Drive Strength**：`[-] Lv<n> · 高阻/低阻 Ω [+]` 增减档（无 drv_sel 寄存器或未配置时禁用并说明）。
- **状态区**：`LOGIC HIGH/LOW (0/1)` 大字显示最近 0x50 读值 + `Read 0x50` 按钮 + `Mask 0x... · bank bit N · drv addr [hi:lo]`。

### 6.4 右键菜单

- **Set Function** 二级菜单：列出该脚 `func_options`（iomux 复用功能名，GPIO 在前，checkable 勾选当前值），选中即 OP_BITS 写 func_sel 位域；未配置 func_sel 时禁用。
- **Export Config** 二级菜单：Output High / Output Low / Input Pull-Up / Input Pull-Down 四种模式收集进 Export Manager（三元组去重；pull 未配置时对应项禁用）。

### 6.5 底部读取条

- **READ 主按钮**：立即读当前 bank Base+0x50 输入电平。
- **Poll 0x50**：周期下拉（200/500/1000/2000 ms，默认 500）+ Start/Stop Poll 开关；每 tick 空闲时读当前 bank，忙碌自动跳过；运行中改周期即时生效。

### 6.6 Export Manager（Matrix 右侧，≥1 条目才显示）

- 条目列表（GPIO 名 + 模式 + 行内删除 / Clear 清空）；**按芯片持久化**到 `get_user_data_dir("gpio")/export_items.json`，Detect/Load 时校验恢复（范围 / mode / pull 支持）。
- **Merged Script Preview**：合并为单段 WRITE_BITS 脚本——段名 = 首脚全名 + 其余脚数字部分 + `_Config`（如 `GPIO05_62_63_Config`，同脚去重）；每脚动作块前 `  - //GPIO名_mode` 注释；动作 = func_sel 前置 +（输出模式补 PU/PD 清 0）+ `build_mode_actions`，统一 `_write_bits_line` 转行（set/clear 单 bit 整写转位域写）。
- **Exec**（绿色 `#gpioExec`）：全部条目动作经统一管道一次下发 DUT，完成后延迟全量回读。
- **Export**：脚本复制到剪贴板。

## 7. 视图 2：Register Map

- **Raw Access**：ADDR / DATA 两个 `HexWheelLineEdit` + `Write32`（OP_WRITE 整写）/ `Read32`（结果显示于右侧）——底层调试入口，**不自动 func_sel 前置**。
- **Refresh Readable**：回读当前 bank 全部可读寄存器（VAL_IN / PU / PD / DRV / FSEL 卡片）。
- **寄存器卡片**（两列网格，按当前 bank 动态生成）：
  - `VAL_SET / DIR_SET / VAL_CLR / DIR_CLR`（set/clear 语义说明，值为影子）；`VAL_IN`（+0x50，点击卡片或 R 钮回读）；`DRV_GPIOxx`（每寄存器 8 脚×bits_per_gpio）；`FSEL_GPIOxx`（功能复用选择）；`PU_REG / PD_REG`（1bit/脚；地址未配置显示 TBD 且禁用写）。
  - 每卡 32 个 bit 钮（BIT31~0）：set/clear 卡点击 = 对应位整写；drv/fsel 卡点击 = 所在位域值翻转后 OP_BITS 位域写；pu/pd 卡点击 = 该位取反位域写；`val_in` 卡点击 = 触发回读。可读卡片的 bit 钮带 `rd` 绿色高亮区分。

## 8. 视图 3：I2C Sniffer

- 页面所有 I2C 流量（WRITE32 / READ32 / CHIP_CHECK / ERROR）以带时间戳（ms）条目记录：原始文本 + HTML 着色（类型 / 地址 / 数据 / 语义描述分色）。
- 每次写操作自动生成**语义描述**（`_describe_write`）：Output/Dir set/clr → 涉及引脚列表；PU/PD RMW；Func sel（含功能名）；Drv strength（含档位阻抗）；无法识别回退 Raw。读操作同理（`_describe_read`）。
- **过滤**：All / WRITE32 / READ32 / CHIP_CHECK / ERROR 类型 chip 钮 + 地址/语义关键字搜索框（实时重渲染）。
- **Pause / Resume**：暂停自动滚动刷新（条目仍入缓存）；**Clear** 清空；**Export .log** 导出带芯片头的日志文件（用户自选路径）。

## 9. 视图 4：JSON Config

- 显示 / 编辑当前芯片配置文件 `chips/gpio_configs/<chip>.json`（Detect / Load / Apply 后自动加载）。
- **Import JSON**：从本地磁盘导入到编辑器（不生效，需 Apply）。
- **Export JSON**：编辑器内容导出为 JSON 文件。
- **Reload**：放弃修改，从磁盘重载。
- **Apply Config**：JSON 语法校验 → `gpio_banks` 非空校验 → 写回 `chips/gpio_configs/`（按 JSON `chip` 字段命名）→ 重新加载配置并生效：Profile 下拉同步（新芯片自动加项）、会话复位、视图重建、全量回读。错误显示在红色 `gpioJsonErr` 行。

## 10. 视图 5：Confirm Note（硬件确认清单）

5 张确认卡片，各自带状态标（Confirmed 绿 / To Confirm 琥珀 / Connected 等）：

1. **PU / PD pull register addresses**：逐 bank 列出 PU/PD 地址（TBD 标出），全配齐才 Confirmed。
2. **Drive strength levels and impedance (drv_sel)**：逐 group 寄存器地址 + 位域格式 + 档位范围 + 是否配置阻抗表。
3. **I2C 7-bit device address and width**：main-die 32bit 地址空间说明 + 当前会话 dev（未连接显示 Not Connected）。
4. **Communication bridge**：USB-I2C 物理桥（I2CInterface DLL，Worker 异步）说明。
5. **Pin function sel (mux as GPIO)**：func_sel 基地址 / 位宽 / 有效 group / 自动前置 GPIO 功能值说明（含 RegMap/Raw 不自动前置的提醒）。

## 11. 执行管道与线程模型

- **统一下发管道 `_apply_actions(actions, label, on_done)`**：嗅探（Sniffer + Activity Logs）→ 影子更新（`_apply_to_shadow`）→ `GpioApplyWorker` 硬件下发；未完成操作忙时拒绝并提示。
- **统一读取管道 `_read_registers(pairs, on_done)`**：`GpioReadBanksWorker` 异步读取；结果写 `_in_value` / `_reg_shadow` 并逐条打 `[I2C] READ addr = data 语义`。
- **func_sel 前置**：配置 `func_sel` 段后，任何 GPIO 状态控制（方向 / 电平 / 上下拉 / drv / 批处理 / 掩码）前自动把对应脚 sel 位域写为 GPIO 功能值（影子已等于则跳过）；RegMap 位翻转 / Raw 不自动前置。
- **`_defer_read`**：Worker finished 槽链里再起读线程统一延迟 ≥50ms（页内单发 QTimer，重复延迟合并为最后一次）。
- **线程安全**：QThread 不挂父对象；worker → 页面信号均为绑定方法连接（页面销毁自动断开）；`finished` 经 `_on_worker_done` 单点分发、`thread.finished` 自清理（deleteLater）；`_on_thread_cleanup` 以 sender 校验避免旧线程晚到清新引用。
- **清理**：`cleanup_threads()`（CleanupMixin 契约）停轮询 / 旋转 / 延迟定时器并等待 Worker 退出（≤2s）；`closeEvent` 复用。

## 12. AI 动作登记

构造收 `ui_action_registry`，`_register_ai_ui_actions()` 以白名单登记只读 / 会话态动作（handler 复用原按钮槽，`page_key="gpio"`）：

| id | 说明 | enabled_when |
|---|---|---|
| `gpio.detect` | Detect DUT | 非忙 |
| `gpio.load_profile` | Load Profile | 已 Detect 且非忙 |
| `gpio.read_all` | 全量回读 | 就绪且非忙 |
| `gpio.refresh_regmap` | RegMap 可读寄存器回读 | 就绪且非忙 |
| `gpio.poll_toggle` | 0x50 轮询开关 | 轮询中或就绪空闲 |
| `gpio.sniff_export` | 导出 Sniffer 日志 | 有缓存条目 |

**写 DUT 硬件状态的操作（电平 / 方向 / 上下拉 / drv / Raw / Mask）不登记**，引导用户手动或用 Export Config 脚本流。日志枢纽契约：`self.logs_frame = self.execution_logs`。

## 13. 独立运行

```powershell
python ui/pages/gpio/gpio_control_ui.py
```

经 `ui.standalone.run_standalone_widget` 以 1600×950 窗口独立启动（自动加载 kk_lab.ico）。
