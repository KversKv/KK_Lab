# ui/pages/module_test — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。

## 加载指针（AI 按需拉取）

- **新增 / 修改测试流程** → @see [docs/ai/07_TEST_GUIDE.md](../../../docs/ai/07_TEST_GUIDE.md)
- **编排内核** → @see [core/module_test/](../../../core/module_test/)（`_runner_base` / `mode_manager` / `_common` / `result_model`）

## 本模块职责与边界

- **职责**：Module Test（LDO / DCDC）隐藏 Tab 容器。
- **上游**：`ui/main_window.py` / nav_controller；**下游**：`core/module_test/` runner + items。
- **铁律**：UI 仅交互；`core/module_test/` 无 QtWidgets。

## 接口契约（对外不可破坏）

- `ModuleTestUI` 构造透传：`n6705c_top / mso64b_top / chamber_ui / instrument_manager / ui_action_registry`。
- `TEST_TAB_MAP`：`ldo=0 / dcdc=1`；暴露 `set_current_test / get_current_test / _sync_from_top` 供枢纽调用。
- 共享基类 [_base_subpage.py](./_base_subpage.py)：两子页（LDO/DCDC）复用的被测配置区 / AI 契约。

## 局部约定

- `measured` 用 `list[dict]`（非 `{"rows":[...]}`）才能被 `_measured_to_rows` 渲染成正表（quiescent 现为 dict，单列 `dIvin/dIvout/Iq`）。
- quiescent 项：单点差分测（`iq_diff_measure`），CSV 为 `["dIvin (uA)","dIvout (uA)","Iq (uA)"]`；ENABLE 用 DR BIT/EN BIT 单 bit 位写（`set_dut_enable`）。
- **示波器输出电压通道统一走 DUT Config**：基类 `_base_subpage` 的"示波器通道"下拉（`scope_vout_ch_combo`，存整数 `scope_vout_channel` 入全局 cfg），各 scope 测试项（ripple/output_noise/load_transient/line_transient）一律 `cfg.get("scope_vout_channel", 1)` 读取，**禁止**再在各测试项 ParamSpec 里加 `scope_vout_channel`（已收敛）。DCDC `switching_freq` 的 `scope_sw_channel`（SW 节点）属项级，不在此列。
- 添加新测试项时, 对于非供电的电源仪器, 需要先重置仪器状态, 再去进行测试;
- Load Transient Response（LDO/DCDC 共用 `_common.run_load_transient`）：真机流程=开局先 `clear_arb_all_channels()`（ABOR:TRAN + 全通道 VOLT/CURR:MODE FIX，去掉其它通道遗留 ARB）→ CCLoad + Slew MAX + 电流 ARB Pulse（I0/I1 取负，t0=T/2、t1=0、t2=T/2）→ `set_arb_continuous(ch, True)` 勾选 Continuous（**`ARB:COUN INF`，面板 Arb Properties 的 Continuous 复选框；须在形状配置后、arb_on 前写**）→ `restore_arb_trigger_source()`（TRIG:ARB:SOUR IMM，须在 INIT:TRAN 之前写源；armed 后写源报 +308，BUS+*TRG 后置不触发）→ `arb_on`（INIT 即启动连续脉冲）→ 示波器先 `close_all_channels()` 关掉其它通道 + `set_waveform_intensity(100)`（波形强度 100%，便于看清过冲/欠冲；两驱动均已加此方法，DSOX4034A=`:DISPlay:INTensity:WAVeform`，MSO64B 部分固件不支持则 best-effort 忽略）→ 设 scale/offset/timebase → **settle≥1s**（改时基/scale 后示波器需重新采集稳定，0.5s 会截到过渡帧致平线/单沿）→ `stop()` 暂停采集 → 截图 + Vmax/Vmin/Vmean 算过冲/欠冲 → 每组收尾 `arb_stop`+`set_arb_continuous(ch,False)`+`exit_arb_current`；参数用 ptype="groups"（`transient_groups()`，默认 3 组 I0/I1/频率，弹窗 `_GroupsEditor` 可增删，无 base_key 全量返回）；CSV 第 0 列为组号，截图键 `{"Iload (mA)": str(组号)}` 借 `_shots_table_html` 的 iload 回退列（idx=0）并入报告。示波器 scale=vspan/3 留余量防削波、时基=period/2（10 格整屏约 5 个完整周期）。
- Line Transient Response（LDO/DCDC 共用 `_common.run_line_transient`）：同 Load 流程，仅把拉载换为 Vin 电压脉冲——Vin 通道置 PS2Q + 电压 ARB Pulse（Vin0/Vin1 正电压，t0=T/2、t1=0、t2=T/2），收尾 `arb_stop`+`exit_arb_voltage`+`channel_off`；参数用 `line_transient_groups()`（默认 3 组 Vin0/Vin1/频率）；DCDC 侧为本次新增项（`dcdc_line_transient`，注册表默认不勾选）。
- **示波器测量自动扩量程**：Load/Line Transient 测 Vmax/Vmin/Vmean/Vpp 一律走 `_common._measure_with_autoscale`——波形削波时两驱动对无效值（9.9e37）都会抛异常（DSOX4034A=`MeasurementError`、MSO64B=`ValueError`），助手按量程×2 重试最多 4 次；**重试前必须 `run()` 恢复采集再 settle**（停采状态改量程拿不到新波形），成功返回实际量程，被扩大时 UI 日志提示。曾因此整组记 0 且无截图（异常发生在截图之前）。

## 局部坑点

- 样式走全项目标准：`_setup_style = get_page_base_qss() + get_table_qss() + START_BTN_STYLE + page_extra`，色值只取 `ui.theme` token；启停按钮 objectName 固定 `primaryStartBtn` / `stopBtn`。严禁把 `START_BTN_STYLE`（整段带选择器的 QSS）嵌进 `#xxx { ... }` 声明块——无效 QSS，样式静默失效。
- 结果落 `Results/`；新增测试项落 `core/module_test/{ldo,dcdc}/items/`。
- **逐点截图进报告**：测试项把每张示波器截图追加到 `measured["screenshots"]`（`[{"Iload (mA)":.., "png":路径}]`）。`report.py` 的 `_shots_table_html` 按 `Iload (mA)` 列把截图并入"完整测试数据"表最后一列（缩略图），点击经 `#shotbox` 灯箱放大看原图（Esc/点击关闭）；`_measured_to_rows` 已剔除该键，设了 screenshots 时 `waveform_png` 单图被抑制避免重复。Load Capability&Ripple（LDO/DCDC 共用 `_common.run_load_capability_ripple`）即此模式：扫负载逐点测 Vout+Vpp/RMS 并截屏到 `screenshots/` 子目录。
- **示波器连接联动**：mixin 的 `_on_mso64b_top_changed` 只更新 `scope_connected`，不刷新测试项表；子页基类必须覆盖它并追加 `_refresh_scope_item_state()`（running 时除外），否则连接示波器后 (scope) 项仍显示"未接示波器，跳过"且禁用，需切换页面才恢复。
- **ItemParamsDialog override 语义**：无 `base_key` 的项级参数（reg_addr/msb/lsb/min/max_code 等）`get_override()` 必须全量返回（显示即生效）；曾用"与 prefill diff"语义，被 msb/lsb 联动改写的 max_code 会被误判"未改"而丢弃，致 Output Voltage Scan 误用默认 reg_addr=0x0 扫错寄存器。有 base_key 的基类参数才用 diff（未改回退基类 cfg）。
- **按钮钉高（QSS 盒模型）**：钉死按钮高度用纯 QSS `min-height == max-height`，**不要**用 `setFixedHeight()`（会被 QSS min-height / sizeHint 以 min/max 约束盖住而失效）。总高 = content(min/max-height) + 上下padding + 2×border(1px)，故目标 35px 需 `min/max-height:33px; padding:0`（33+0+2=35）。在 `page_extra` 用 `#objectName` 覆盖（拼接在 `START_BTN_STYLE` 之后），可压过其 `min-height:36px` 与全局 `padding:6px`。


## 开发环境
- N6705C真机地址:TCPIP0::K-N6705C-06098.local::hislip0::INSTR
- MSO64B真机地址:TCPIP0::10.31.31.202::inst0::INSTR
- DSOX4034A真机地址:TCPIP0::10.31.30.181::inst0::INSTR
- 优先使用DSOX4034A进行真机测试
