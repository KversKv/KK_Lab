# ui/pages/gpio — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 本模块职责与边界

- **职责**：DUT GPIO 控制页（TOOLS 组）——Detect DUT → GPIO 网格 → 单脚 模式/电平/drv 控制。
- **下游**：`core/gpio/`（配置 + Worker）；页面**禁止**直接发 I2C。
- **功能说明**：页面全部功能清单见 [GPIO_CONTROL_UI.md](./GPIO_CONTROL_UI.md)（功能变更时同步维护）。

## 局部约定

- **文件布局（2026-10 拆分，仿 ADR 005 / serialCom Mixin 范式）**：`gpio_control_ui.py` 瘦壳入口（类属性 / `__init__` / `append_log` / `closeEvent` / `__main__` 独立运行与打包入口不动），`GpioControlUI` 多继承装配子包 [gpio_control/](./gpio_control/)：`style.py`（`_GPIO_PAGE_QSS`）、`utils.py`（`_icon`/`_fmt32` 等纯函数）、`pin_card.py`（`_PinCard`）、`view_build.py`（全部 `_build_*`）、`state_refresh.py`（影子派生 + 视图刷新 + `_set_status`）、`ops_mixin.py`（Worker 管道 + Detect/Batch/Poll/Raw/Pin/Drv/Inspector + `cleanup_threads`）、`features_mixin.py`（Sniffer/JSON/Export/Notes/AI 注册）；方法名与原巨石一致，跨 Mixin 调用一律经 self；新增方法按职责落对应 Mixin。
- **新芯片 JSON 配置**：模板在 [json_example/](./json_example/)（`NEW_CHIP_JSON_TEMPLATE.md/.txt` 空模板 + `NEW_CHIP_JSON_1701.txt`/`NEW_CHIP_JSON_1607.txt`/`NEW_CHIP_JSON_3601p.txt` 已填写示例），让用户填模板后据此生成 `chips/gpio_configs/<chip>.json`；字段规则见 `core/gpio/gpio_config.py`，参考成品 `chips/gpio_configs/bes1701.json`。
- **寄存器偏移硬约定**（各 bank 一致，见 `core/gpio/gpio_config.py`）：Out Set=+0x00 / Dir Set=+0x04 / Out Clr=+0x0C / Dir Clr=+0x10 / Input Read=+0x50；每 bank 32 GPIO，bit=(group%4)*8+pin。
- **芯片配置**：`chips/gpio_configs/<chip_name>.json` 按 `bes_chip_check()` 的 `chip_name` 匹配；bank 可选 `groups` 字段声明有效 group 数（默认 4，钳位 1~4；高位 group 物理不存在时使用，如 BES1701 仅 18 group → AON_GPIO4 `groups=2`，GPIO180~197 不显示/不参与批处理与统计，`group_count`=各 bank groups 求和）；drv_sel 支持两种寻址——`drv.group_bases` per-group 显式地址表（每寄存器 8 脚×bits_per_gpio，pin N 位域 [4N+3:4N]，地址区可不连续，BES1701 用此）或 `drv.base` 线性区（bits_per_gpio=2→16脚/寄存器，4→8脚/寄存器；可选 `drv.pins_per_field`（默认 1）= 相邻 N 脚共用一个位域同档同调，BES1607 用此：=2、4bit/16 档，GPIO 2k/2k+1 共享 field=(group*8+pin)//2，每寄存器 16 脚×4 寄存器覆盖双 bank，UI 无需特判——同对两脚由同一字段取值/回读自然一致）；`drv.base` 亦可配为逐寄存器地址列表（允许地址区不连续/空洞，null=该寄存器无 drv，如 BEST3601P：Group0~9 @0x40086050~0x40086060、Group10~11 跳至 0x40086078）；`drv.levels`+`out_high/low_ohm` 档位阻抗表驱动 UI 增减档（[-] Lv [+]）并取整显示 Ω，`pull_ohm` 为输入上下拉阻抗；PU/PD 各一个独立寄存器区（1bit/GPIO），地址 null 时 UI 自动禁用上下拉按钮。
- **设备地址/位宽**：固定 BIT_32，dev 取 `chip_info["main_die_i2c_addr"]`（0x11/0x31 自适应）。
- **GPIO 命名**：`GPIO{group}{pin}`（Group0→GPIO00~07，Group1→GPIO10~17）；bank 内位号显示 `BIT{bit:02d}`。卡片与 Inspector 均以 GPIO 名为显眼主标签、BIT 位号为暗淡副标签；RegMap 的 DRV/FSEL 寄存器卡片以起始脚 GPIO 名命名（`DRV_GPIO00`/`FSEL_GPIO00`）。
- **Ctrl 多选**：`_selected_pins` 有序列表（`_selected` 为主选中=最后点击）；卡片 `mousePressEvent` 透传 modifiers，Ctrl+Click 切换累加，普通点击/卡片动作钮/切 bank/会话复位均重置为单选或清空。多选（≥2）时 Inspector 切三容器显隐——`_insp_single_box`（别名+信息）/`_insp_multi_box`（选中列表，行=GPIO名+模式+移除）/`_insp_state_box`（大字电平+mask）；配置区统一生效：方向/电平按 `_selected_by_bank()` 合掩码+func_sel 掩码前置一次 `_apply_actions`，pull/drv 逐脚动作拼接一次下发，统一 `_queue_banks_read` 回读受影响 bank；使能规则=全体为输出才放电平、全体支持 pull/drv 才放对应钮，drv 混档显示 `Lv a~b`。
- **线程链**：Worker finished 槽链里再起读线程统一走 `_defer_read`（页内单发 QTimer ≥50ms，重复延迟合并；03§26）；QThread 不挂父对象，`finished` 经 `_on_worker_done` 绑定分发，关窗清理走 `cleanup_threads()`（已注册 CleanupMixin；03§39）。
- 方向寄存器只有 set/clear 无回读地址，模式状态仅本页会话内记忆。
- **Detect / Load Profile 后自动全量回读**：`_start_read_all_banks` 读全部 bank 0x50 电平 + PU/PD + drv + func_sel 可读寄存器同步影子与引脚卡片；每次读回在 Activity Logs 打 `[I2C] READ addr = data 语义`（`_on_read_done`），轮询每 tick 同样会打。
- **影子寄存器模型**：页面以 `_dir_shadow` / `_out_shadow`（按 bank）与 `_reg_shadow`（按地址，PU/PD/drv/任意写）维护会话影子；引脚模式、上下拉、drv、统计计数全部由影子推导，所有写操作（含批处理/掩码/位翻转）统一走 `_apply_actions()` 管道（嗅探→影子→硬件 Worker）。
- **仅真机控制**：无仿真模式——所有读写必须经 `core/gpio/` Worker 到 USB-I2C 硬件；`_ready()` = 已加载配置且 `dev_addr` 已知（即必须先 `i2c.bes_chip_check()`，Load Profile 也需先 Detect）。
- **func_sel 前置**：JSON 配 `func_sel` 段后，控制 GPIO 状态（方向/电平/上下拉/drv/批处理/掩码注入）前自动把对应脚 sel 位域写 `gpio_value`（`_func_sel_pin_actions` / `_func_sel_mask_actions`，影子已等于则跳过）；RegMap 位翻转 / Raw 底层入口不自动前置。
- **func_sel.functions 功能表**：JSON `func_sel.functions` 存 iomux 复用功能名（键 `GPIO_P{G}_{P}` → [Func_0..N]，list index=sel 位域值，null=未用；BES1701 源自 `Temp/bes1701_iomux.xlsx`，`tests/gen_bes1701_iomux.py` 注入）；core 侧 `func_name()`/`func_options()`。卡片 GPIO 名后（alias_label 前段）显示当前功能名（影子推导，未命名值回退 `0xN`）；右键 **Set Function** 二级菜单列 `func_options`（GPIO 在前，checkable 勾选当前值），选中即 OP_BITS 写 sel 位域。
- **5 视图 Tab**（QButtonGroup + QStackedWidget）：Matrix/RegMap/Sniffer/JSON/ConfirmNote；页面级 QSS 常量 `_GPIO_PAGE_QSS` 一次性 `setStyleSheet`，控件高度一律 QSS `min-height==max-height` 钉死。**例外**：顶栏 `#gpioTab` 禁钉高度——`dut_sub`（DUT 芯片/Bank 信息）与标题组成两行竖排块，Tab 按钮靠 `QSizePolicy.Expanding` 垂直撑满顶栏（高度 = 标题行 + 副标题行）。
- **图标资源**：顶栏品牌图标 = `resources/icons/gpio-pins.svg`；独立打包/窗口图标 = `resources/icons/gpio_control_ui.ico`；`gpio_control_ui.spec` 的 `icon=` 与 `__main__` 的 `setWindowIcon` 同指向，换图标需同步替换 .ico。
- **AI 接入（datalog/power_analyser 同模式）**：构造收 `ui_action_registry`，`_register_ai_ui_actions()` 仅登记只读/会话态动作（detect/load_profile/read_all/refresh_regmap/poll_toggle/sniff_export，page_key=`gpio`），**写 DUT 硬件状态的操作（电平/方向/上下拉/drv/Raw/Mask）不登记**；`self.logs_frame = self.execution_logs`（枢纽日志契约）；profile 在 `core/ai/profiles.py` 的 `AI_PROFILES["gpio"]`，记忆键 `"gpio"` → `tools/gpio`。
- **Pin Matrix 右键 Export Config**：卡片右键收集 `(group,pin,mode)` 入 `_export_items`（输出高/低、输入上/下拉，三元组去重；pull 未配置时禁用对应项），≥1 条时 Matrix 右侧自动展开 Export Manager（`_build_export_manager`，行内删除/Clear 减项，Export 复制剪贴板）；脚本合并为单段：段名 = 首脚全名 + 其余脚数字部分 + `_Config`（如 `GPIO05_62_63_Config`，同脚去重），每脚动作块前 `  - //GPIO名_mode` 注释；动作 = func_sel 前置 +（输出模式补 PU/PD 清 0）+ `build_mode_actions`，统一 `_write_bits_line` 转 WRITE_BITS 行（set/clear 单 bit 整写转位域写）；动作构造抽出 `_export_item_actions()` 供脚本与 **Exec 按钮**（Export 左侧，绿色 `#gpioExec`）复用——Exec 将全部条目动作一次走 `_apply_actions()` 下发 DUT 并 `_defer_read` 全量回读；列表按芯片持久化 `get_user_data_dir("gpio")/export_items.json`（增删清即写），`_reset_session_state` 时 `_load_export_items` 校验恢复（范围/mode/pull 支持）。

## 局部坑点

- **页面 UI 文本一律英文**（Label/按钮/ToolTip/Activity Logs）；Inspector 的 Direction/Output Level/Drive Strength 标签不带寄存器偏移解释，按钮不显示偏移量；Output Level 与方向联动——INPUT 时 Inspector HIGH/LOW 与卡片电平按钮禁用置灰。
- **set/clear 寄存器整写**即可（写 1 生效位）；**PU/PD/drv 是普通 RW 寄存器**，必须 OP_BITS 位域写（DLL RMW），禁整写覆盖其他脚。
- **stack 页 / QScrollArea viewport 背景发白**：默认浅 palette（standalone/离屏）下二者不继承页面 QSS 底色，必须给视图页与滚动容器显式 `setObjectName("gpioViewPage")` / `QScrollArea` 命名 `gpioScroll` 并在页 QSS 钉背景色，否则嵌入/独立运行中间区域发白。
