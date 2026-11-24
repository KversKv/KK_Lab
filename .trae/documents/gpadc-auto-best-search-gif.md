# GPADC Auto Best 搜索过程 GIF 导出实施计划

## Context

Auto Best 已保存完整搜索顺序、端点比较、Repeat 指标和代表曲线，但当前只能导出静态图和 Excel。用户需要可嵌入文档的 GIF，直观展示 Start/End/Mid 初始化、逐次半区收缩及最终最佳校准点。已确定使用现有 Pillow，每个唯一候选一帧，不展开 Repeat、不重新访问仪器、不改变 Runner 协议。

## 实施方案

### 1. 离线时间轴

在 `core/pmu_test/gpadc/gpadc_analysis.py` 新增 `build_linearity_auto_search_timeline(result)`：

- 以 `auto_search.evaluated_values` 为时间轴，按 `n_value` 回查 groups；禁止把按数值排序的 groups 当搜索顺序。
- 按比较所需 `left_value/right_value/mid_value` 已齐备的顺序插入 comparison 事件，并校验记录一致性，避免错误回放。
- 每个 candidate 保存真实评价前缀、当前候选 group、当前区间及当前前缀最佳值；comparison 保存收缩前后区间、方向和 noise tie。
- 最后事件标记 `is_final` 并延长停留；单候选自然退化为单帧。停止结果允许导出完整候选并标记 `search incomplete`，缺组或非法顺序直接拒绝。
- 当前最佳按可见候选前缀使用现有 `select_best_linearity_group(..., noise_aware=True)`，不直接套最终 best_index。

### 2. 独立双面板帧渲染

新增 `ui/pages/pmu_test/gpadc_test/search_gif_renderer.py`，不操作页面现有图表：

- 使用离屏 pyqtgraph/QImage 渲染固定 1200×760 画布，上图累积显示可见候选的真实代表 Repeat Error 曲线，下图按评价顺序连接候选 Max Abs 中位数并显示搜索区间、当前候选和当前最佳。
- 全动画固定坐标范围，旧曲线淡化、当前候选高亮、当前/最终最佳强调；文本标明 Candidate、Representative Repeat、Median Max Abs/RMS、单位和 noise tie。
- comparison 帧不新增曲线，只更新保留半区和方向；最终帧突出 best_index/terminal_value，停止时明确 `Best evaluated — search incomplete`。
- 每帧转成 RGB bytes + 宽高/stride/duration 的不可变数据，不传 QImage/QWidget 给后台。

### 3. 非阻塞 GIF 编码与导出生命周期

新增 `core/pmu_test/gpadc/gpadc_gif.py`：Pillow 将 RGB 帧编码为共享 128 色调色板 GIF，candidate 700ms、comparison 1000ms、最终事件 2800ms、`loop=0`；写临时文件后原子改名，停止/异常删除半成品。

在 `export_mixin.py` 管理 `idle → rendering → encoding`：

- GUI 线程用页面持有的 QTimer 每次仅渲染一帧，避免同步循环阻塞；渲染完成后用独立 QThread + 现有 `TestWorker` 执行纯 Pillow/文件 IO。
- 再次点击或页面清理可停止：渲染阶段取消 timer，编码阶段 `request_stop()`，不在 UI 线程 wait；完成/异常均 Signal/Slot 回主线程复位。
- 导出期间禁止启动新测试或重复导出；现有 `_export_data`、可见图表和 `_chart_image_bytes` 保持不变。

### 4. UI、AI 与文件输出

- `layout_mixin.py` 在 Export Result 旁新增 `Export Search GIF`，仅 Linearity 页显示；有有效 Auto Best 结果且空闲时可用，导出中切换为 Stop 文案。ft_only 不显示。
- `config_ai_mixin.py` 增加 `pmu_gpadc.export_search_gif` 命名动作，复用同一入口和可用条件，返回“已启动”而非提前宣称成功。
- 输出到 `Results/`：`GPADC_AutoBestSearch_<Chip>_<Channel>_<Case>_<timestamp>.gif`，命名三要素复用 `_naming_fields()` 并清理 Windows 非法字符。
- 普通遍历或缺少候选时不允许导出；停止的 Auto Best 可导出已完整候选。

### 5. 同步与打包

- `spec/kk_lab.spec` 增加 `PIL.GifImagePlugin`；`spec/pmu_gpadc.spec` 通过 `EXTRA_HIDDENIMPORTS` 加入同一插件。Pillow 已在 requirements，无新增依赖。
- 更新 `DIRECTORY_STRUCTURE.txt`（两个新源码文件）、`helps/pmu_gpadc.html` 和 `ui/pages/pmu_test/AGENTS.md`。

## 验证

1. 扩展 `tests/refactor/test_pmu_analysis.py`：验证 `[0,20,10] → comparison → 5 → comparison …` 的真实顺序、区间/当前最佳、单点、相邻点、停止和非法记录。
2. 扩展 `tests/test_gpadc_worker_threading.py`：离屏渲染候选/比较/最终帧，验证尺寸和帧差异；Pillow 回读 GIF 的帧数、时长、循环及末帧停留；覆盖停止、异常清理、按钮/AI 可用状态及现有图表不被修改。
3. 运行完整 GPADC Worker/UI/Mock 回归、算法测试及所有修改 Python 文件 Ruff；核对 spec 与同步矩阵，正式产物仅写 `Results/`。
