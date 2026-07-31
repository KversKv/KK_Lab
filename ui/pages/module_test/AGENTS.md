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
- **示波器输出电压通道统一走 DUT Config**：基类 `_base_subpage` 的"示波器通道"下拉（`scope_vout_ch_combo`，存整数 `scope_vout_channel` 入全局 cfg），各 scope 测试项（ripple/output_noise/load_transient/line_transient/switching_freq）一律 `cfg.get("scope_vout_channel", 1)` 读取，**禁止**再在各测试项 ParamSpec 里加 `scope_vout_channel`（已收敛）。
- 添加新测试项时, 对于非供电的电源仪器, 需要先重置仪器状态, 再去进行测试;
- **Test Item 运行状态（2026-07 新增）**：runner 新增 `item_started(str)` 信号（每项跑前发射），子页基类据此把清单切为运行状态——`_enter_run_state` 锁定勾选框（`Qt.ItemIsEnabled`，运行期禁改勾选）并在"判定/记录"列显示 等待中(warning)/未选(muted)，`_mark_item_running`→▶进行中(info)，`_mark_item_done`→✓PASS(success)/✗FAIL(error)/✓完成(info,N/A)。`_on_finished`/`_on_failed` 调 `_exit_run_state` 恢复默认（勾选可交互+记录列复原"记录"）。`_refresh_scope_item_state` 加了 `is_test_running` 守卫，运行期顶层连接同步不得覆盖状态列。
- **逐项 setForeground 被全局 QSS 盖掉（坑）**：`get_table_qss()` 在 `QTableWidget` 选择器设了 `color: text_secondary`，widget 级 QSS color 优先级**高于** item 的 ForegroundRole，导致运行状态色全灰。修复=测试项表 `_make_items_table` 实例级 `setStyleSheet("QTableWidget { color: palette(text); }")` 关掉 QSS 调色板（只影响本表实例，不改共享 QSS），逐项 `setForeground` 才生效。**任何要靠 setForeground 做逐项染色的 QTableWidget 都需此招**。
- Load Transient Response（LDO/DCDC 共用 `_common.run_load_transient`）：真机流程=开局先 `clear_arb_all_channels()`（ABOR:TRAN + 全通道 VOLT/CURR:MODE FIX，去掉其它通道遗留 ARB）→ CCLoad + Slew MAX + 电流 ARB Pulse（I0/I1 取负，t0=T/2、t1=0、t2=T/2）→ `set_arb_continuous(ch, True)` 勾选 Continuous（**`ARB:COUN INF`，面板 Arb Properties 的 Continuous 复选框；须在形状配置后、arb_on 前写**）→ `restore_arb_trigger_source()`（TRIG:ARB:SOUR IMM，须在 INIT:TRAN 之前写源；armed 后写源报 +308，BUS+*TRG 后置不触发）→ `arb_on`（INIT 即启动连续脉冲）→ 示波器先 `close_all_channels()` 关掉其它通道 + `set_waveform_intensity(100)`（波形强度 100%，便于看清过冲/欠冲；两驱动均已加此方法，DSOX4034A=`:DISPlay:INTensity:WAVeform`，MSO64B 部分固件不支持则 best-effort 忽略）→ 设 scale/offset/timebase → **settle≥1s**（改时基/scale 后示波器需重新采集稳定，0.5s 会截到过渡帧致平线/单沿）→ `stop()` 暂停采集 → 截图 + Vmax/Vmin/Vmean 算过冲/欠冲 → 每组收尾 `arb_stop`+`set_arb_continuous(ch,False)`+`exit_arb_current`；参数用 ptype="groups"（`transient_groups()`，默认 3 组 I0/I1/频率，弹窗 `_GroupsEditor` 可增删，无 base_key 全量返回）；CSV 第 0 列为组号，截图键 `{"Iload (mA)": str(组号)}` 借 `_shots_table_html` 的 iload 回退列（idx=0）并入报告。示波器 Y 轴量程固定从 10 mV/div 起步（`init_scale_v=0.01`，削波由 `_measure_with_autoscale` 翻倍重试、Load/Line Transient 均 `max_tries=5`，即 10→20→40→80→160 mV/div；注册表已无 `transient_vspan_mv` 参数）、时基=period/2（10 格整屏约 5 个完整周期）。
- Line Transient Response（LDO/DCDC 共用 `_common.run_line_transient`）：同 Load 流程，仅把拉载换为 Vin 电压脉冲——Vin 通道置 PS2Q + 电压 ARB Pulse（Vin0/Vin1 正电压，t0=T/2、t1=0、t2=T/2），收尾 `arb_stop`+`exit_arb_voltage`+`channel_off`；参数用 `line_transient_groups()`（默认 3 组 Vin0/Vin1/频率）；DCDC 侧为本次新增项（`dcdc_line_transient`，注册表默认不勾选）。
- **示波器测量自动扩量程**：Load/Line Transient 测 Vmax/Vmin/Vmean/Vpp 一律走 `_common._measure_with_autoscale`——波形削波时两驱动对无效值（9.9e37）都会抛异常（DSOX4034A=`MeasurementError`、MSO64B=`ValueError`），助手按量程×2 重试（Load/Line 均 `max_tries=5`，从 10 mV/div 起步翻倍）；**重试前必须 `run()` 恢复采集再 settle**（停采状态改量程拿不到新波形），成功返回实际量程，被扩大时 UI 日志提示。曾因此整组记 0 且无截图（异常发生在截图之前）。
- **Load Transient 首组额外 settle（2026-07）**：`run_load_transient` 首组（idx==0）在示波器初始化（关通道/设强度/改时基量程）后 settle 额外 +3s——首次采集建立更慢，避免首帧不稳。`settle = max(1.0, 60×时基) + (3.0 if idx==0 else 0.0)`。
- **报告记录仪器 \*IDN?（2026-07）**：`ModuleTestResult.instruments`（list[dict]，runner 开局 `_collect_instruments` 采集）→ `build_report_data` 填 meta.instruments，前端按 `name/model/sn` 渲染。取 IDN 优先级：`identify_instrument()`（示波器）→ `identify()` → `.instr.query("*IDN?")`（N6705C 无 identify，靠此）。失败静默跳过不阻断测试。MockN6705C 的 `.instr`（MockInstr.query 返回 ""）会得空串被跳过，故 Mock 报告无仪器行（真机才有）。
- **Transient 截图 settle（2026-07 真机调试）**：`run_load_transient` / `run_line_transient` 改时基/通道后先 `ctx.scope.run()` 再 `settle(max(1.0, 60×(period/2)))`（**等待 60×时基**让 DSOX 在新时基下采满一屏并刷新显示），然后 `_measure_with_autoscale`（内部 stop+测量）返回时直接截图，**不再多余 run/stop**。两个坑：①改时基前必须确保示波器在 run 态——停采态下改时基只是把旧波形重绘，settle 再久也采不到新波形（截图定格在过渡帧）；②时基后 settle 必须够长——低频大时基组（10Hz=50ms/div）采满+刷新较慢，短 settle（如 6×时基=0.3s 或固定 1s）会让 autoscale 的 stop 定格在未采满的空帧/旧帧上（调试 settle 截图的 ~2.2s 传输延迟曾"碰巧"掩盖此问题，去掉调试代码即复现）。
- **全自动流程通道自控（2026-07 修订）**：VIN 通道不干预（DUT 上电态由前置工序保证），其余通道每项开局强制入位——`setup_meter_channel` = VMETer + range + **channel_on**（曾缺 channel_on 致 measure_voltage 恒 0）；`setup_load_channel` 支持 `initial_current_a`，**先写电流再 channel_on**，消除沿用上一项末点电流的危险窗口；CCLoad **开启状态禁设 0mA**（硬红线 12），故 `teardown_load` 只 `channel_off` 不归零；dcdc_efficiency 的 baseline 改在负载通道开启前测；dcdc_quiescent 删掉 load 通道配置（外供 Vout 源已够，0mA 拉载无意义且触红线）。`run_vout_scan` 不再裸 `set_mode`，改走 `setup_meter_channel`。
- **Line Transient 收尾不关 VIN**：`run_line_transient` 收尾改 `set_voltage(vin_v)` 恢复正常输出，曾 `channel_off(vin_ch)` 把 DUT 掉电，致全自动流程后续项全挂。
- **ARB 残留清理**：`clear_arb_all_channels` 的 `ABOR:TRAN` 被裸 except 吞掉且未等 initiated 清零就写 `VOLT/CURR:MODE FIX`（连续脉冲时清除慢，此时写 FIX 报 +308 被忽略），Load Transient 的 `CURR:MODE ARB` 会残留到 Line Transient。transient 项开局改走 `_common._reset_arb_state`：先 `arb_stop` + 全通道 [1,2,3,4] `wait_arb_idle`，再对本项通道显式 `exit_arb_voltage` + `exit_arb_current` 回固定输出态；**其它通道（本项不用的）额外 `set_arb_shape(ch, "NONE")`（`ARB:FUNC:SHAP NONE,(@ch)`，即面板 "No Arb Configured"）清掉遗留形状配置，避免 BUS 触发误带起旧通道脉冲**。本项通道不置 NONE（马上要被重新配置新形状）。驱动侧 `set_arb_shape` 为本次新增（真机 + Mock 同步）。
- **Quiescent 收尾关断外供而非设 0V**：`quiescent` 收尾曾 `setup_source_channel(vout_src_ch, 0.0)`——PS2Q 模式下设 0V 仍 `channel_on`，会把 DUT 的 VOUT 节点拉到 0V 致异常；改 `channel_off(vout_src_ch)` 关断外供通道。关断**前**还须还原 ENABLE 寄存器：`set_dut_enable` 成功时返回写入前 (dr, en) 原始位值，`iq_diff_measure` 第 4 个返回值带出，调用方用 `restore_dut_enable(ctx, en_regs, d[3])` 还原（差分测末尾 DUT 处于关断态，不还原则后续项在 DUT 关断下跑）。
- **示波器通道显示联动**：`run_load_capability_ripple` 开局显式 `set_channel_display(scope_ch, True)`——上一项 transient 调过 `close_all_channels()`，不显式开则 ripple 全程平线；`_measure_with_autoscale` 重试耗尽抛异常时外层先 `ctx.scope.run()` 恢复采集再降级，避免示波器停在 stop 态污染下一组/项。
- **DCDC Switching Frequency 改版（2026-07）**：从"探 SW 节点单点测频"改为"扫负载 + AC 耦合测输出纹波频率"——参数收敛为 `vin_bias()` + `load_sweep()` + `average_cnt()` + `settle_time()`（删除 `scope_sw_channel`/`fsw_load_ma`/`fsw_expected_khz`，示波器通道走 DUT Config）；每负载点 `set_AutoRipple_test` 自动优化档位后按平均次数测 `get_channel_frequency` 取均值；**收尾必须恢复 `set_channel_coupling(ch, "DC")`**，否则后续 transient 等 DC 测量项测不到直流分量；`measured` 用 `list[dict]`（`Iload (mA)`/`Fsw (kHz)`），report 加 `switching_freq` 的 Fsw-Iload 曲线分支。

## 局部坑点

- 样式走全项目标准：`_setup_style = get_page_base_qss() + get_table_qss() + START_BTN_STYLE + page_extra`，色值只取 `ui.theme` token；启停按钮 objectName 固定 `primaryStartBtn` / `stopBtn`。严禁把 `START_BTN_STYLE`（整段带选择器的 QSS）嵌进 `#xxx { ... }` 声明块——无效 QSS，样式静默失效。
- 结果落 `Results/`；新增测试项落 `core/module_test/{ldo,dcdc}/items/`。
- **逐点截图进报告**：测试项把每张示波器截图追加到 `measured["screenshots"]`（`[{"Iload (mA)":.., "png":路径}]`）。report.py（2026-07 重构为 REPORT_DATA JSON + 原生 JS/SVG 单文件报告，无 CDN）将其转为 `items[].attachments`（base64 dataURI），渲染为缩略图网格 + 灯箱（←/→/Esc、滚轮缩放）；有 screenshots 时 `waveform_png` 单图仍被抑制避免重复。Load Capability&Ripple（LDO/DCDC 共用 `_common.run_load_capability_ripple`）即此模式：扫负载逐点测 Vout+Vpp/RMS 并截屏到 `screenshots/` 子目录。报告数据出口唯一：`build_report_data(result)` → `build_module_html_report` 注入模板；测试项异常标注走 `table.rules`（前端规则引擎 gt/lt/abs_gt/eq/outlier/constant 求值）。
- **示波器连接联动**：mixin 的 `_on_mso64b_top_changed` 只更新 `scope_connected`，不刷新测试项表；子页基类必须覆盖它并追加 `_refresh_scope_item_state()`（running 时除外），否则连接示波器后 (scope) 项仍残留"未接示波器"提示，需切换页面才恢复。
- **测试项勾选与启动校验（2026-07 改版）**：所有测试项**始终可勾选**，未接示波器不再禁用/反勾选 (scope) 项，仅在记录列显示"未接示波器"提醒；启动测试时由 `_missing_instruments(cfg)` 统一校验全程所需仪器（N6705C + 勾选项的示波器依赖，DEBUG_MOCK 放行），缺仪器则 `_on_start_test` 记 `[ERROR]` 日志并弹 `QMessageBox` 阻断启动，`ai_start_test` 同步返回失败原因。
- **ItemParamsDialog override 语义**：无 `base_key` 的项级参数（reg_addr/msb/lsb/min/max_code 等）`get_override()` 必须全量返回（显示即生效）；曾用"与 prefill diff"语义，被 msb/lsb 联动改写的 max_code 会被误判"未改"而丢弃，致 Output Voltage Scan 误用默认 reg_addr=0x0 扫错寄存器。有 base_key 的基类参数才用 diff（未改回退基类 cfg）。
- **按钮钉高（QSS 盒模型）**：钉死按钮高度用纯 QSS `min-height == max-height`，**不要**用 `setFixedHeight()`（会被 QSS min-height / sizeHint 以 min/max 约束盖住而失效）。总高 = content(min/max-height) + 上下padding + 2×border(1px)，故目标 35px 需 `min/max-height:33px; padding:0`（33+0+2=35）。在 `page_extra` 用 `#objectName` 覆盖（拼接在 `START_BTN_STYLE` 之后），可压过其 `min-height:36px` 与全局 `padding:6px`。
- 注意单个测试项的鲁棒性, 例如通道的设置顺序, 是否需要额外的等待时间, 测试前主动打开通道, 测试后是否需要关闭通道等. 注意Vbat通道不需要关闭, 因为它是DUT电源, 关闭会导致DUT电源异常.
- N6075C禁止在CC Load模式下设置0mA负载电流输出, 在0mA的测试场景中, 应该是直接关闭CC Load的输出, 而不是设置0mA Load;并且也禁止从0mA的情况下开机CC Load通道; 需要先设置非0mA负载电流, 才能开启CC Load通道.

## 开发环境
- N6705C真机地址:TCPIP0::K-N6705C-06098.local::hislip0::INSTR
- MSO64B真机地址:TCPIP0::10.31.31.202::inst0::INSTR
- DSOX4034A真机地址:TCPIP0::10.31.30.181::inst0::INSTR
- 优先使用DSOX4034A进行真机测试
