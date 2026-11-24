# GPADC N/P 双寄存器线性度遍历实施计划

## Context

现有 Linearity Traverse 仅支持单 Trim Register。需要改为 `n_weight` 与 `p_weight` 两个寄存器，并通过滑动开关支持两种模式：
- **Link N = P 开启（默认）**：共用当前 Start / End / Step，逐点写入 `(N=v, P=v)`，不是矩阵。
- **Link N = P 关闭**：N、P 分别设置 Start / End / Step，按 **N 外层、P 内层** 执行完整 N×P 矩阵遍历。

每组继续复用 Force Voltage 扫压和独立两点校准，只显示 Error 曲线；Max Abs Error 最小为最佳，并列比较 RMS；不入 Recent，结束后恢复双寄存器原值。

## 实施步骤

1. **改造参数区与动态切换**
   - 修改 `ui/pages/pmu_test/gpadc_test/mixins/layout_mixin.py`：单 Trim 地址改为 N Weight Register、P Weight Register，新增 `Link N = P` 滑动开关。
   - 保留共享 Start/End/Step 容器，新增 N Weight Sweep 与 P Weight Sweep 两套独立范围容器；开关开启只显示共享范围，关闭只显示独立范围。
   - 复用 `_ToggleSwitch`，toggled 与配置回填统一调用显隐函数；所有新控件纳入运行期禁用。

2. **配置、解析与启动参数**
   - `config_ai_mixin.py` 贯通 `linearity_n_reg_addr`、`linearity_p_reg_addr`、`linearity_link_np`，共享 `linearity_start/end/step`，以及独立 `linearity_n_*`、`linearity_p_*` 范围键；不保留旧单 Trim 键。
   - `execution_mixin.py` 校验双地址非负；链接模式仅解析共享范围，独立模式分别校验 N/P 的 Start<=End、Step>0 和 IIC Width 上限，并向 Runner 传递完整快照。

3. **实现同值与矩阵组合遍历**
   - `gpadc_analysis.py` 复用 `generate_linearity_values`，新增组合生成纯函数：链接模式生成 `[(v, v)]`，独立模式按 N 外 P 内生成笛卡尔积。
   - `analyze_linearity_group` 改为接收 N/P，组结果保存 `n_value/p_value`；最佳排序键改为 `(max_abs_mv, rms_mv, n_value, p_value)`。
   - `gpadc_runner.py` 每组依次写 N、P 后调用既有 `_sweep_force_voltage`；总进度按“当前组索引 + 组内扫压进度”映射，停止仍丢弃当前半组。

4. **双原值与异常安全恢复**
   - 写入前读取并保存 `original_n/original_p`；结果元数据保存双地址、Link 状态和对应范围。
   - `finally` 按 P、N 逆序独立恢复；P 恢复失败不得阻断 N，恢复错误只记录并提示，不覆盖原结果或原异常。

5. **更新曲线、AI 与导出**
   - `plotting_mixin.py` 的图例和最佳摘要改为 `N=0x…, P=0x…`，最佳曲线仍最后绘制、加粗，其余淡化。
   - `execution_mixin.py` 的日志和 AI params 改为 `best_n/best_p`，保留空结果与无 Recent 行为。
   - `export_mixin.py` 的 Summary 增加模式、双地址、双原值和相应范围；组表及 Sweep Data 将 Trim 列拆为 N Weight、P Weight，并继续嵌入 Error 图。

6. **测试与文档同步**
   - 更新 `tests/refactor/test_pmu_analysis.py`：同值组合、矩阵顺序、独立校准及 N/P 并列规则。
   - 更新 `tests/test_gpadc_worker_threading.py`：双写顺序、矩阵进度、成功/停止/异常双恢复、P 恢复失败仍恢复 N、停止半组和零完整组；UI 验证开关显隐、独立范围校验、配置回填、Mock 矩阵曲线及双列导出。
   - 精简同步 `helps/pmu_gpadc.html` 与 `ui/pages/pmu_test/AGENTS.md` 的 Linearity Traverse 契约。

## 验证

- `python -m pytest tests/test_gpadc_worker_threading.py tests/refactor/test_pmu_analysis.py -m "not qt"`
- `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gpadc_worker_threading.py -m qt`
- 对全部修改 Python 文件运行 `python -m ruff check`。
- DEBUG_MOCK 分别跑同值遍历与独立矩阵遍历，核对组数、N/P 写入顺序、最佳曲线、双寄存器恢复和导出；真机效果后续实验室验证。
