# GPADC Linearity Auto Best P0/P1 优化计划

## Context

当前 Auto Best 仅比较区间端点，首轮会把 `0x3BD4` 所在半区错误丢弃；该方法对非对称单峰也不成立，且 Repeat=1 时 Noise Tie 没有统计意义。本次需要：

- P0：实现数学正确的离散单峰搜索，Tie 不再固定丢弃一侧。
- P1：实现全范围粗扫、多低谷 Step=1 细扫、少量 Finalist 加强复测。
- 保留 Auto OFF 的现有全量遍历作为全局基准，不改变手动 Link、独立 N/P、扫压校准及寄存器/电源恢复语义。
- 使用 `user_data/page_configs/pmu_test/gpadc.json` 做真机验证，且不回写用户配置。

## 1. 搜索策略与配置

在 Auto Best 下增加英文 Strategy 下拉：

- `Coarse + Fine (Multi-Basin)`：`coarse_fine`，默认；旧 JSON 缺少策略键时映射到此项。
- `Unimodal (Fast)`：`unimodal`，保留已知单峰场景的快速搜索。

新增唯一配置键 `linearity_auto_strategy`，贯通布局、get/apply config、执行参数和 Excel Summary。Auto OFF 或 Link OFF 时忽略策略，原行为不变。粗扫参数使用 core 常量，不增加额外 UI 参数。

## 2. P0：正确的离散单峰搜索

修改 `core/pmu_test/gpadc/gpadc_analysis.py` 的 `advance_linearity_auto_best`，保留纯函数入口和缓存协议：

1. 剩余整数不超过 4 个时，升序补齐全部未测点，避免小区间方向误判。
2. 宽区间取 `m=(low+high)//2`，测量并比较 `m` 与 `m+1`，不再要求或比较 Start/End：
   - `m` 明确更优：保留 `[low,m]`；
   - `m+1` 明确更优：保留 `[m+1,high]`。
3. 精确/Noise Tie：区间不变，方向记为 `hold`；选择最长连续未测段的中点继续补测，直至出现有效方向或区间内点已测全。不得默认向左缩区。
4. 每轮必须新测一个唯一点、有效缩区或完成；Runner 增加状态迭代上限，防止空转。进度按唯一候选数上界计算，允许 Tie 安全退化为密集搜索。
5. 仅完整 Repeat 的候选进入缓存；最终仍从完整已测组中选 Best Evaluated。

比较记录改为内部探针对及显式前后区间。`build_linearity_auto_search_timeline` 按新记录重建候选/收缩/Hold 帧；Coarse+Fine 使用候选帧和当前细扫区间，继续复用现有 GIF Renderer，不伪造端点二分帧。

## 3. P1：Coarse → Fine → Finalist

在 `gpadc_analysis.py` 增加小型纯函数，在 `gpadc_runner.py` 编排，复用 `_sweep_force_voltage`、`_evaluate_linearity_auto_candidate`、`aggregate_linearity_repeats` 和缓存：

1. **Coarse**：默认步长 `0x10`，包含 Start/End；范围不超过 33 个整数时直接全范围 Step=1。
2. **低谷识别**：按 `(Median Max Abs, Median RMS, Value)` 比较，保留不大于左右邻点的内部低谷及边界低谷；平台点保留，至少包含粗扫全局最佳点。
3. **Fine**：每个低谷生成 `Value±0x10` 闭区间，裁剪到搜索范围，重叠或相邻区间合并；逐区间 Step=1 补测，缓存命中不得重复写 N/P 或扫压。
4. **Finalist**：每个合并区间先取一名胜者，再按相同指标排序取前 3；不足 3 个时从全部已测点补足不同 Value。
5. **加强复测**：Finalist 目标总次数为 `min(10,max(3,UI Repeat+2))`。已有 Repeat 结果保留，只追加缺少的次数并重新聚合代表曲线/中位数/波动带；追加过程中 Stop 不污染上一次完整结果。
6. **最终选点**：正常完成时只在完成加强复测的 Finalist 中选 Best；中途 Stop 时回退为最佳完整已测候选，并标记搜索未完成。

`auto_search` 保持原有顶层字段，新增 `strategy/coarse_values/fine_values/neighborhoods/finalist_values`。`evaluated_values` 仅记录首次完整测量的唯一 Value，Finalist 复测不重复追加。Excel 继续导出全部 Repeat 明细，Summary 改显示真实策略及阶段信息。

当前范围 `0x3B00～0x3C00` 的粗扫为 17 点；单低谷时典型为 47 个唯一候选，Repeat=1 时约 53 次扫压。多低谷/平台允许安全退化，但唯一候选绝不超过 257 个。

## 4. 文件改动

- `core/pmu_test/gpadc/gpadc_analysis.py`：P0 状态机、P1 纯函数、timeline。
- `core/pmu_test/gpadc/gpadc_runner.py`：策略分发、缓存调度、Finalist 追加 Repeat、日志与进度。
- `ui/pages/pmu_test/gpadc_test/mixins/layout_mixin.py`：Strategy 下拉、使能状态和 Tooltip。
- `ui/pages/pmu_test/gpadc_test/mixins/config_ai_mixin.py`：新键持久化与默认值。
- `ui/pages/pmu_test/gpadc_test/mixins/execution_mixin.py`：策略传入 Runner。
- `ui/pages/pmu_test/gpadc_test/mixins/export_mixin.py`：Summary 策略和阶段数据。
- `tests/refactor/test_pmu_analysis.py`、`tests/test_gpadc_worker_threading.py`：更新旧预期并补回归。
- `helps/pmu_gpadc.html`、`ui/pages/pmu_test/AGENTS.md`：同步策略契约。
- `tests/verify_gpadc_linearity_real.py`：独立真机验证入口，不被 pytest 自动收集，不实例化 ConfigMemory。

不修改手动遍历、独立 N/P 矩阵、电源快照恢复、P→N 寄存器恢复和找到 Best 后不自动写回的语义；不新增依赖或打包资源。

## 5. 验证

### 自动测试

- P0：1/2/3/4 点、小区间、缓存命中、边界最优、非对称单峰、平台/Noise Tie、状态迭代上限。
- 以日志三点指标为锚点构造最优点 `0x3BD4` 的非对称单峰模型，断言能够评估并选中它。
- P1：粗扫端点、边界/多个/平台低谷、邻域合并、缓存无重复 IO、每低谷 Finalist、追加 Repeat 聚合、正常/停止时 Best 范围。
- 保持 Auto OFF 全量和 Link OFF 矩阵原测试不变；成功/停止/异常均核验 N/P 与电源恢复。
- 更新配置 round-trip、Summary、GIF 帧及全部 Repeat 导出测试。
- 运行目标 pytest、既有 GPADC 测试、Ruff；再按项目门禁运行非 Qt/Qt 回归。

### 真机实测

1. 真机脚本只读加载当前 JSON，在内存转换成 Runner 配置；从 `resources/instrument_addresses.json` 读取 N6705C A，使用真实 `I2CInterface`，`DEBUG_MOCK=False`。
2. 先执行 `--dry-run`，只输出范围、粗扫点数和候选上界，不创建仪器/I2C。
3. 台架可用时分别运行 `unimodal` 和默认 `coarse_fine`；除命令行显式覆盖外沿用 JSON 的 CH1、3.0～5.0V/0.1V、50样本、IIC/N/P 参数。结果 JSON 与日志写 `Results/`。
4. 核对候选评价顺序、低谷邻域、Finalist 次数、`auto_search.completed`、Best Max Abs/RMS，以及 `0x3BD4` 是否被实际评估；不把某个固定误差值写成通用通过条件。
5. 每次结束独立确认 P→N 原值恢复、CH1 电压/模式/输出恢复；关闭 I2C/VISA，并比对运行前后用户 JSON 哈希确保未回写。
