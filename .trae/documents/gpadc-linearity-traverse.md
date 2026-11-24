# GPADC Linearity Traverse 实施计划

## Context

GPADC 需要在现有 Force Voltage Test 基础上增加 Linearity Traverse：对线性度寄存器的多个配置分别执行同一组 Voltage Sweep，将所有校准后的 Error 曲线叠加显示，并高亮最佳配置。复用当前 GPADC 的 Mixin、core Runner、QThread Worker 和两点校准体系，不新增仪器驱动。

已确认：
- “Recet”指 **Recent Tests**；仅新测试项隐藏且不写入 Recent，其他测试项不变。
- 最佳配置按全电压点 **Max Abs Error 最小**判定；并列时比较 RMS Error。
- 测试完成、停止或异常后均恢复线性度寄存器原值，不自动回写最佳值。
- 结果区只保留 Error 多曲线，不显示 Mean、Min-Max、旧性能指标卡或 Curve View。

## 实施步骤

1. **注册测试项**
   - 在 `ui/pages/pmu_test/gpadc_test_ui.py` 增加 `TEST_LINEARITY_TRAVERSE = "Linearity Traverse"` 与 N6705C 仪器映射。
   - 在 `layout_mixin.py` 的测试下拉中将其放在 Force Voltage Test 后；kind 使用 `linearity_traverse`，不加入 Recent Compare 的 `_CURVE_KINDS`。

2. **增加参数与切换行为**
   - 在 `layout_mixin.py` 的 Test Parameters 中增加独立 Linearity Settings 区：Trim Register (Hex)、Start (LSB)、End (LSB)、Step (LSB)。
   - 复用 Force Voltage 的 Voltage Sweep、校准点、Points、Voltage Channel、采样算法和离群筛选控件；复用 Data Acquisition 的 Device Address 与 IIC Width 做整寄存器读写。
   - 新测试项显示 Voltage Sweep 和 Linearity Settings，隐藏指标卡、Recent 按钮/面板及 Curve View 菜单；切回其他测试项时恢复其原有可见性。
   - 将新增输入纳入运行期禁用列表。

3. **启动校验与配置传递**
   - 在 `execution_mixin.py` 增加解析和校验：仅支持 IIC；地址/配置值支持十进制或 `0x` 十六进制整数；Start <= End、Step > 0，配置值不得超出现有 IIC Width 对应范围。
   - 沿用 Force Voltage 的电压范围校验，传递 `linearity_reg_addr/start/end/step` 及原扫压参数；非法输入在创建 Worker 前拒绝启动。

4. **实现嵌套遍历与最佳值分析**
   - 在 `core/pmu_test/gpadc/gpadc_runner.py` 注册新 kind，并纳入现有 N6705C 电源快照/恢复流程。
   - 从 `_run_force_voltage` 提取可复用的单次扫压私有 helper，保持原 Force Voltage 返回协议与响应保护不变。
   - 新流程先读取并保存 Trim 原值，然后按 Step 遍历配置；每个配置整寄存器写入后调用同一扫压 helper。Step 语义与原 Voltage Sweep 一致，不额外补不可达的 End 点。
   - 每组使用相同手动/自动校准点独立调用 `compute_calibration`，计算 `error_mv = (mean_cali - input_voltage) * 1000`、Max Abs Error 与 RMS Error。
   - 在 `gpadc_analysis.py` 放置配置序列、单组分析及最佳组选择的纯函数；最佳排序键为 `(max_abs_mv, rms_mv, trim_value)`，保证并列结果稳定。
   - 结果保留公共 Voltage 轴、各组 Trim/K/B/Mean Cali/Error/统计/原始扫压数据、`best_index` 和 `stopped`。停止时丢弃当前未完成组，仅返回已完整采集的组；采集或校准异常明确报错，不静默跳组。
   - 用 `try/finally` 恢复 Trim 原值；恢复失败复用 `_report_cleanup_error` 记录并提示，不覆盖原结果或原异常。组内进度换算为总进度，保持单调。

5. **绘制 Error 多曲线并完成结果分发**
   - 在 `plotting_mixin.py` 新增专用绘图：单图 X=Input Voltage (V)、Y=Error (mV)，附零误差线；普通曲线使用现有调色板并淡化，最佳曲线全不透明、加粗并标注 Best Trim 与 Max Abs Error。
   - 在 `execution_mixin.py` 增加完成分支和空结果保护，输出最佳配置日志，保存图表快照及 `_export_data`；不计算或显示 Force Voltage 的 INL/DNL/ENOB 等卡片。
   - 新 kind 跳过 `_record_recent_test`，且不得把此前 Recent 记录误设为当前 `_loaded_record`；保留开始测试时的内部 `_reset_result_display()`。

6. **配置记忆与导出**
   - 在 `config_ai_mixin.py` 的 get/apply 配置中增加四个 Linearity 键，保留地址和配置值的输入文本格式，使 ConfigMemory 与 AI 回填一致；AI 结果摘要提供 Best Trim、Max Abs Error、RMS Error。
   - 在 `export_mixin.py` 增加专用分支：Summary 保存遍历参数、各组指标及最佳配置，Sweep Data 保存 Trim/Voltage/Error 和必要原始数据，并嵌入当前 Error 图；输出到项目根 `Results/`，不在 git 追踪路径生成 XLSX。

7. **同步与测试**
   - 更新 Runner/测试中“六类流程”数量描述，精简同步 `ui/pages/pmu_test/AGENTS.md` 的 GPADC 新项契约及 `helps/pmu_gpadc.html` 参数说明；核对 `docs/ai/08_CHECKLISTS.md` 同步矩阵，不改无关文档。
   - 扩展 `tests/refactor/test_pmu_analysis.py`：配置序列、独立校准、Max Abs/RMS 最佳选择和并列规则。
   - 扩展 `tests/test_gpadc_worker_threading.py`：新结果协议、写入/扫压顺序、总进度，以及成功/停止/异常路径的 Trim 与电源恢复；回归原 Force Voltage 结果。
   - 使用 Qt offscreen 做页面冒烟：切换新项后参数/Recent/指标显隐正确，Mock 完成多组扫压后只生成 Error 多曲线并高亮最佳组，Recent 不新增记录。

## 验证命令

- `python -m pytest tests/test_gpadc_worker_threading.py tests/refactor/test_pmu_analysis.py -m "not qt"`
- 相关 Qt 用例使用 `QT_QPA_PLATFORM=offscreen` 运行。
- `python -m ruff check` 检查本次修改文件。
- 通过 GPADC 页面选择 Linearity Traverse，以 DEBUG_MOCK 跑通启动、停止、完成、导出和测试项往返切换；真机寄存器效果需后续实验室验证。
