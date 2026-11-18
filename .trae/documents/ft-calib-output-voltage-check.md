# FT Calibration Check — Output Voltage Check 子页实施计划

## Context

`ui/pages/pmu_test/ft_calib_check_ui.py` 容器的 "Output Voltage Check" 子 Tab 目前是占位（`_build_output_voltage_placeholder`）。需实现完整功能：

1. **芯片管理**：每芯片多个 DCDC/LDO rail（Vbit 位域 + EFUSE 映射），页面内管理对话框 + `user_data/` JSON 持久化、可导入导出。
2. **测压仪器可选**：Keysight 34461A DMM（新建页内连接卡）或 N6705C VMeter（复用现有连接 Mixin）。
3. **核心流程**：读 EFUSE（脚本链路 / 普通 I2C 直读可选）→ 偏移/绝对双模式算校准码 → 写 Vbit 位域调压 → 测 DUT 电压 → 与目标电压（配置值或 code×步进+基电压）按容差判 PASS/FAIL；逐 rail 顺序执行，可选测后恢复原寄存器。

用户已确认四项决策：页面内管理+JSON；EFUSE 脚本+直读双链路；偏移/绝对双模式+误差判定；新建 DMM 连接卡+仪器下拉。

## 已读指引

`ui/pages/AGENTS.md`、`ui/pages/pmu_test/AGENTS.md`（就近继承根 AGENTS.md）；探索覆盖 06_PAGE_GUIDE / 07_TEST_GUIDE / 03_GOTCHAS / ui/modules / lib/i2c 约定。

## 一、新建文件

### core（analysis 零 Qt，worker 仅 QtCore）

| 文件 | 职责 |
|---|---|
| `core/pmu_test/ft_calib_ov/__init__.py` | 包导出 |
| `core/pmu_test/ft_calib_ov/ft_calib_ov_analysis.py` | 纯函数：`extract_bits(raw,msb,lsb,signed)`（补码符号扩展）、`insert_bits`、`compute_code(mode,base_code,efuse,offset)`（offset=base+efuse+offset；absolute=efuse+offset）、`clamp_code`、`resolve_target_mv(rail,code)`（config 直取 / derived=code×step_mv+base_voltage_mv）、`judge(measured_v,target_mv,tol_mv)`（\|err\|≤tol 判 PASS）、`validate_chip_config/validate_rail`（非法抛 ValueError）、`summarize`（total/passed/failed/max_abs_err/overall） |
| `core/pmu_test/ft_calib_ov/ft_calib_ov_store.py` | 芯片库 JSON：`load_library/save_library`（`get_user_data_dir("ft_calib_ov_chips")/chip_library.json`，tmp+os.replace 原子写，损坏回落空库）、`merge_import`（重名冲突清单供 UI 确认）、`export_chips`；schema_version=1 |
| `core/pmu_test/ft_calib_ov/ft_calib_ov_worker.py` | `FtCalibOvWorker(QObject)`：信号 `log_message(str)/rail_result(dict)/result_update(dict)/test_finished(bool,str)`；注入 chip 快照/options/n6705c/dmm/debug_flag/i2c_factory；`request_stop()` 软停止；流程见下 |

### ui

| 文件 | 职责 |
|---|---|
| `ui/pages/pmu_test/ft_calib_ov_check_ui.py` | `FtCalibOvCheckUI(N6705CConnectionMixin, QWidget)` 子页：布局/启停编排/结果表+指标卡+误差图/导出/ConfigMemory/AI 契约。构造 `(n6705c_top=None, instrument_manager=None, ui_action_registry=None)`（registry 传 None，容器统一登记，同 GPADC 嵌入惯例） |
| `ui/pages/pmu_test/ft_calib_ov_chip_dialog.py` | `ChipManagerDialog` + `RailEditDialog`（均 parent=self、apply_qss "dialog"、#cfgSection 分组、OK/Cancel 二元化） |
| `ui/pages/pmu_test/ft_calib_ov_dmm_card.py` | 页内私有 `_DmmConnectionCard`：VISA 扫描/手填 + 后台连接 Worker。**不抽 ui/modules Mixin**（当前唯一真实消费者，避免公共组件回归成本；clk 页 DMM 是 stub 不算第二消费者） |

### tests（DEBUG 临时文件一律进 tests/）

- `tests/core/test_ft_calib_ov_analysis.py`：analysis/store 纯函数单测（`-m "not qt"`）。
- `tests/test_ft_calib_ov_smoke.py`：offscreen 容器冒烟 + DEBUG_MOCK worker 端到端（`-m qt`）。

## 二、芯片配置 JSON schema

```json
{ "schema_version": 1, "chips": [{
  "name": "BES1307PH",
  "i2c": { "device_addr": "0x27", "width_flag": 10, "speed_khz": 100 },
  "efuse": { "link": "script| i2c", "script_filename": "efuse_1307ph.py",
             "chip_name": "1307ph", "device_addr": "0x27", "width_flag": 10, "speed_khz": 100 },
  "rails": [{
    "name": "VDCDC0", "type": "DCDC|LDO", "enabled": true,
    "vbit": { "reg_addr": "0x0035", "msb": 7, "lsb": 0, "width_flag": null },
    "efuse_field": { "reg_addr": "0x0001", "msb": 15, "lsb": 0, "signed": false },
    "mode": "offset|absolute", "base_code": "0x80", "offset_lsb": 0,
    "step_mv": 6.25, "base_voltage_mv": 900.0,
    "target": { "source": "config|derived", "voltage_mv": 1100.0 },
    "tolerance_mv": 20.0, "settle_ms": 20
  }]
}]}
```

- `efuse_field.reg_addr` 双语义：script 链路=EFUSE 偏移地址；i2c 链路=普通寄存器地址（UI 标签随链路切换）。
- `signed` 支持补码 trim；`vbit.width_flag=null` 继承芯片级。
- 测量参数（samples/NPLC/range）与 restore/stop-on-fail 为**页面级**，不进 rail schema。
- 运行期 rail 勾选（selected_rails）进 ConfigMemory，不进芯片库。

## 三、Worker 流程（范式 = output_voltage_worker.py L110-156 / L374-395）

1. `validate_chip_config` 全量校验（仪器操作前）；筛 enabled∩selected rails，空则拒绝。
2. worker 内临时建 I2C（`I2CInterface`，DEBUG_MOCK→MockI2C），用完即关；script 链路且非 mock 时 `EFuseScriptCaller(i2c.raw)`（**MockI2C 无 .raw/close，hasattr 守卫，mock 下脚本链路降级直读并 log [MOCK]**）。
3. 仪器准备：VMeter→`set_mode(ch,"VMETer")`+`channel_on`（仅测压，绝不 CCLoad）；DMM→`configure_voltage_dc(range)`+`set_nplc`。仪器实例由 UI 连接卡持有传入，worker 不创建/断开 VISA。
4. 逐 rail（每步查 stop）：
   - EFUSE：script→`caller.read_efuse(dev,reg,I2CWidthFlag,I2CSpeedMode,script,chip_name)`，失败即中止整轮（保守，避免错码调压）；i2c/mock→`i2c.read` 直读；`extract_bits` 提取（signed 可选）。
   - `compute_code`→`clamp_code`（越界 log [WARN] 不中止）。
   - 位域 RMW：读原值→restore 开启时按寄存器去重登记（保留首次原值）→`insert_bits` 写→readback 校验（mismatch log [WARN] 入结果）。
   - settle 分片 sleep（≤20ms/片逐片查 stop）。
   - 测量：VMeter→`measure_voltage(ch)`（3 次均值）；DMM→`measure_average("VOLTage:DC",samples,range)` 取 average（min/max/stddev 入结果）。
   - `resolve_target_mv`→`judge`→`rail_result.emit`+`result_update.emit(summarize)`+定宽带单位 [MEAS] 日志行；stop_on_fail 且 FAIL 则 break。
5. 循环走完 success=True（PASS/FAIL 是数据判定，不影响执行成功语义）；停止/异常为失败。
6. finally：restore 开启时逆序恢复全部登记寄存器（覆盖完成/停止/异常；单项失败不阻断其余，恢复失败置 success=False）；关 I2C；`test_finished.emit`。

线程装配走 UI 侧 QThread（clk/gpadc 范式）：moveToThread、started→run、test_finished→quit、收尾交 `thread.finished`；**_stop_test 只 request_stop()+quit()，禁 UI 线程 wait**。EFUSE DLL/DMM averaging 为不可中断阻塞段，stop 粒度=rail 边界+settle 分片（帮助文档注明）。首版不做 confirm_request 弹窗。

## 四、UI 设计

### 子页布局（clk_test_ui 骨架）

左 320px QScrollArea + 右结果区，`ExecutionLogsFrame.wrap_with(content, show_progress=True, stretch=(4,1))`；`get_page_base_qss()`+page_extra（#objectName 钉高度，禁裸 min-height/setFixedHeight 钉按钮）；表格 `get_table_qss()`。

- **Chip 面板**：chip_combo + "Manage Chips..."（运行中禁用）+ rail 摘要表（Run✓/Rail/Type/Mode/Target (mV)/Tol (mV)，Run 可勾选，双击开 RailEditDialog 回写库）。
- **Measurement 面板**：仪器下拉 [Keysight 34461A (DMM) / N6705C VMeter]；DMM 卡或 N6705C 连接卡（`build_n6705c_connection_widgets`）按选择显隐；`vmeter_channel_combo` 必 `register_power_channel_combo`；DMM 参数 samples(1-100 默认10)/NPLC(默认1)/Range(默认AUTO) 仅 DMM 可见。
- **Options**：Restore Registers（默认勾）、Stop on FAIL（默认不勾）。
- start/stop 按钮自带（#primaryStartBtn / #stopBtn，同 siblings）。
- 右栏：指标卡（Rails/Passed/Failed/Max |Error| (mV)/Result 动态配色，数值 label 带单位）+ 结果表（Rail/Type/EFUSE (LSB)/Code/Target (mV)/Measured (mV)/Error (mV)/Tol (mV)/Verdict，PASS 绿 FAIL 红）+ pyqtgraph 误差图（X=rail 序号，Y=Error (mV)，±tol 参考）+ Export CSV。`get_capture_pixmap()` 合成指标卡+结果（不含日志）。
- 启动前校验：芯片已选、≥1 rail 勾选、对应仪器已连接（DEBUG_MOCK 走 Mock）、地址可解析；运行中锁定配置控件。
- worker 持启动时芯片库**深拷贝快照**，运行中库变更不影响在跑测试。

### 芯片管理对话框

左 chip 列表 + Add/Duplicate/Remove（确认弹窗 parent=self）；右芯片级表单（Name/I2C Addr HexWheelLineEdit/Width 8|10|32|88/Speed/EFUSE Link/Script File 下拉=扫描 `lib/i2c/config/EFUSE_SCRIPTS/*.py`/EFUSE Chip Name/Addr/Width/Speed）+ rail 摘要表 + Add/Edit/Remove Rail。**rail 编辑用嵌套 RailEditDialog 表单**（15+ 字段跨字段校验，内联编辑不可承载）：Vbit / EFUSE Field(含 signed) / Calibration(mode/base_code/offset/step/base_voltage) / Target & Judge(source/voltage/tolerance/settle)。OK 时 validate 失败行内红字不关窗。底部 Import/Export（QFileDialog JSON，merge_import 重名确认）。OK→save_library→chips_changed→页面刷新（保留选中名）。

### DMM 连接卡（页内私有）

可编辑 resource combo（`get_address_preset("digital_multimeter","keysight_34461a")` 预填，缺失为空）+ SpinningSearchButton（`VisaIdnScanWorker(("34461","34460","MULTIMETER"))` 串行，禁 UI import pyvisa；DEBUG_MOCK 填 mock 地址）+ Connect/Disconnect 单按钮（enable 成对恢复）。连接走后台 Worker：`factory.create_digital_multimeter("34461a", resource)`+`identify()`（**34461A 构造即连接，无 connect()/is_connected()，必须异步**）；断开同走 Worker `disconnect()`。不接 InstrumentManager（无 DMM 会话类型）；`cleanup_threads()` 回收线程。

## 五、容器改造（关键集成点，已核实）

### ft_calib_check_ui.py

- 占位替换为 `FtCalibOvCheckUI(...)`（属性名保持 `output_voltage_check_ui`，删占位方法）；副标题改 "Per-rail output voltage calibration check via EFUSE-derived trim codes."。
- **新增容器信号 `start_relay/stop_relay`**：两子页各自 start/stop btn.clicked→relay（子页自身槽先连先执行）。根因：PMUTestUI `_connect_subpage_signals`（pmu_test_ui.py L266-278）把 clicked 一次性钉死在构建时的按钮对象，动态 property 无法跟随 tab 切换。
- 契约分发表：
  - `start_test_btn/stop_test_btn/is_test_running` → currentWidget()；
  - `sync_n6705c_from_top/set_system_status/update_instrument_info/cleanup_threads` → **两子页都调**；
  - `sync_chamber_from_manager` → 仅 gpadc；
  - `get_test_config/update_test_result/clear_results/get_test_mode/set_test_mode/get_test_id/set_test_id/get_capture_pixmap` → currentWidget()；
  - `_ai_active_subpage()` → currentWidget()（两子页均实现 AI 契约）；
  - 导出动作 `pmu_ft_calib.export_result` handler/enabled_when 按当前子页分支（GPADC→export_result+_export_data；OV→export_csv+has_results）。不登记模态弹窗类 AI 动作。

### pmu_test_ui.py（唯一改动，约 6 行，仿 psrr 特例 L268-274）

`_connect_subpage_signals` 加 `ft_calib_check` 分支：`ui.start_relay→_on_test_btn_clicked(key,ui)`、`ui.stop_relay→_on_test_stopped(key)` 后 return。`is_test_running` 启动点击时序 quirk 为全子页既存行为，保持同构不修。

## 六、AI / ConfigMemory / 导出 / 收尾同步

- **AI 契约**（OV 子页）：CAP_GET_CONFIG/APPLY_CONFIG/START_TEST/STOP_TEST/GET_RESULT；`apply_config_to_controls(cfg, silent=False)` 单一写入口（线程边界校验+_AI_HIGHLIGHT_QSS 1.5s）；ai_start_test 前置校验；ai_get_result_summary={available,running,chip,summary}。
- **ConfigMemory**：ns `pmu_test/ft_calib_ov`，bind_interface+watch+restore；键 chip_name/selected_rails/measure_instrument/vmeter_channel/dmm_resource/dmm_samples/dmm_nplc/dmm_range/restore_registers/stop_on_fail；地址键存原始文本；芯片库本体独立 store 不进 ConfigMemory；chip_name 缺失降级默认。
- **导出**：`Results/ft_calib_ov_<chip>_<时间戳>.csv`（Results/ 已 gitignore，满足 CSV 禁 git 路径红线），表头带单位。
- **帮助**：`helps/pmu_ft_calib.html` L29-30 占位段替换为完整说明（芯片管理/双 EFUSE 链路/offset·absolute 语义/config·derived 目标/仪器连接/停止与恢复/导出；注明 stop 粒度与 VMeter 精度提示）。
- **同步矩阵**：DIRECTORY_STRUCTURE.txt 登记新文件；ui/pages/pmu_test/AGENTS.md 精简更新（容器分发表/relay/芯片库路径/DMM 卡私有）；docs/ai/memory.md 上下文；spec 收尾核对 EFUSE 脚本 datas 已含（预期不改）；零新依赖。
- UI 文案英文专业简洁；禁 Emoji；禁 print；不增删无关注释；不主动 git commit。

## 七、验证

1. `pytest -m "not qt" tests/core/test_ft_calib_ov_analysis.py`：位提取（signed/边界）、双模式码计算+负偏移、clamp、双来源目标、judge 边界（|err|==tol PASS）、validate 非法、store roundtrip/损坏回落/merge 冲突（monkeypatch get_user_data_dir→tmp_path）。
2. `QT_QPA_PLATFORM=offscreen; pytest -m qt tests/test_ft_calib_ov_smoke.py`：容器构建→切 OV tab→get_test_config 键集→relay 随两子页按钮发射→对话框打开/校验/关闭→ConfigMemory restore→cleanup_threads 幂等；回归既有 pmu_test 相关用例。
3. DEBUG_MOCK 端到端：MockI2C+MockKeysight34461A/MockN6705C 注入同步 run()：2 rail 假芯片→断言结果数/判定/vbit 写入且 finally 恢复原值；中途 request_stop→提前终止且恢复仍执行；script 链路 mock 降级有 [MOCK] 日志；再走 QThread 异步路径验证收尾。
4. 门禁：`python -m ruff check .`、`python -m mypy`、`pytest -m "not qt"`、`pytest -m qt`（.venv 激活）。
5. 真机清单（交付后人工）：EFUSE script 链路先跑 tests/verify_efuse_1307ph.py 基准；单 rail 试跑确认 readback/恢复；DMM 与 VMeter 各一轮比对。

## 八、主要风险

- EFUSE DLL 调用阻塞且 BESI2CIO 类级锁全局串行（与 IIC Tool 页互锁等待），stop 粒度只能到 rail 边界——文档注明，不 terminate。
- signed trim 配错→错码错压：clamp+readback+finally 恢复+EFUSE 失败即中止兜底。
- MockI2C 无 .raw/close：hasattr 守卫+mock 降级直读，不改共享 Mock；真机前必须回归脚本链路。
- VMeter 单次 MEAS:VOLT? 噪声大：3 次均值，帮助提示精密判定优先 DMM。
- DMM 页内私有会话不跨页共享、顶部仪器栏不显示——接受，未来提升 Mixin 时解决。