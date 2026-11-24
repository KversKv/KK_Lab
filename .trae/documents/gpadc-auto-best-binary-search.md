# GPADC Link 模式自动二分寻优实施计划

## Context

当前 Linearity Traverse 只能按 Step(Value) 穷举 N/P 写入值。用户需要在 Shared Step(Value) 下增加 Auto Best 滑动开关：启用后禁用 Step，在 Start/End(Value) 间自动寻找最佳值，并通过可配置重复测量降低波动导致的误判。已确认仅支持 Link N=P；独立 N/P 保持现有矩阵遍历。

## 实施方案

### 1. UI 与配置

- 在 `ui/pages/pmu_test/gpadc_test/mixins/layout_mixin.py` 的 Shared Step 下方新增 `Auto Best`（`_ToggleSwitch`，默认 OFF）和 `Repeat (Runs)`（`QSpinBox`，默认 3、范围 1–10）。
- Auto ON：禁用 Step、启用 Repeat；Auto OFF：恢复 Step、禁用 Repeat。运行中三者均禁用，结束恢复时按 Auto 状态重新计算，独立 N/P 不读取 Auto 配置。
- 新增配置键 `linearity_auto_best` / `linearity_auto_repeat`，贯通 `config_ai_mixin.py` 的 get/apply 与现有 ConfigMemory；保留 Step 原文，不回写或清空。
- `execution_mixin.py::_parse_linearity_inputs` 在 Link+Auto 下只校验 Start/End(Value) 与 Repeat，跳过 Step 内容和数值校验；手动及独立模式校验逻辑不变。

### 2. 纯搜索与波动算法

在 `core/pmu_test/gpadc/gpadc_analysis.py` 增加无 Qt 纯函数，并按需从 `core/pmu_test/gpadc/__init__.py` 导出：

- `normalize_linearity_auto_range(start, end)`：复用有限数、非负、Start<=End 和 `floor(x+0.5)` 取整语义，返回整数闭区间，不读取 Step。
- `advance_linearity_auto_best(low, high, cache)`：首轮依次评价 Start、End、Mid，后续复用已测端点且每轮仅评价新区间 Mid；按端点指标保留更优半区，左端点更优则 `high=mid`，右端点更优则 `low=mid`，相邻整数点直接终止。候选全程缓存不重复，覆盖单点、相邻点和取整后范围塌缩。
- `aggregate_linearity_repeats(repeat_groups)`：Max Abs/RMS 分别取 `statistics.median`，记录 Repeat 数、两指标波动范围及全部 Repeat 明细。顶层代表曲线选用距两个中位数最近的一次真实 Repeat，不拼接虚拟曲线。
- 增加波动感知比较：Max Abs 中位数差超出双方波动带时直接决定；接近时比较 RMS；两者均在波动带内则判并列，固定向低 Value 收缩并记录 `ambiguous`。Repeat=1 不伪造波动带。手动遍历仍使用原精确 `Max Abs → RMS → N/P` 排序。

二分以误差响应近似单峰为前提；非单峰不承诺全局最优，最终结果从全部已评价唯一候选中选取，并明确为最佳已测候选。

### 3. Runner 编排

在 `core/pmu_test/gpadc/gpadc_runner.py` 将现有手动组合评价抽成可复用 helper，新增 Auto 分支，继续复用 `_sweep_force_voltage`、`analyze_linearity_group`、停止检查及统一 `try/finally`：

- 每个唯一 Value 只写一次 N=P，连续执行 Repeat 次完整扫压；收齐后才聚合入缓存。缓存命中不产生仪器 IO。
- Repeat 中途停止或当前扫压不完整时丢弃当前候选，之前完整候选保留；响应保护失败和仪器异常不得误记为用户停止。
- `groups` 按 Value 排序且每个唯一候选仅一项，顶层为代表 Repeat 曲线和中位数指标，`repeat_results` 保存每次完整评价；`best_index` 使用波动感知比较。
- 增加 `auto_search` 元数据：规范化范围、评价顺序、区间比较/波动带、终止值和 `ambiguous`；`linearity` 保存 Auto/Repeat 配置。
- 进度按理论最大候选数×Repeat 估算并单调封顶 99，正常结束才到 100。结束仍按 P→N 恢复原寄存器，外层电源快照恢复不变，不自动写回最佳值。

### 4. 绘图、AI 摘要与导出

- `plotting_mixin.py` 继续每个唯一候选绘制一条代表 Error 曲线；Auto 摘要注明 Repeat 中位数及波动并列提示。
- `execution_mixin.py` 保持现有结果协议，补充 `auto_best/auto_repeat/sweep_count/search_ambiguous` 参数供 AI 摘要使用；`group_count` 始终表示唯一候选数。
- `export_mixin.py` 的 Summary 增加 Auto、Repeat、搜索轨迹/歧义和候选波动范围；Auto 的 Sweep Data 增加 Repeat/Representative 列并展开 `repeat_results`，手动导出结构与行数保持兼容。

### 5. 文档与局部契约

同步 `helps/pmu_gpadc.html` 和 `ui/pages/pmu_test/AGENTS.md`：说明 Auto 仅 Link、Step 禁用、Repeat 中位数、波动并列、单峰假设及不自动写回最佳值。无新增依赖、目录或打包资源。

## 验证

1. 扩展 `tests/refactor/test_pmu_analysis.py`：整数边界、相邻/单点、左右单调及二次单峰、缓存与对数级评价数、奇偶 Repeat 中位数、代表 Repeat、波动带并列和非单峰“最佳已测候选”。
2. 扩展 `tests/test_gpadc_worker_threading.py`：可控指标注入验证二分方向、每候选 Repeat 次、缓存无重复 IO、独立模式不受 Auto 残留影响、Repeat 内停止/异常、进度和 N/P/电源恢复。
3. Offscreen 验证开关/Repeat/Step 状态、配置往返、Auto 跳过非法 Step、Mock 曲线唯一候选数及 XLSX Repeat 明细；手动矩阵回归不变。
4. 运行相关 pytest（Qt 使用 `QT_QPA_PLATFORM=offscreen`）及所有修改 Python 文件的 Ruff 检查。
