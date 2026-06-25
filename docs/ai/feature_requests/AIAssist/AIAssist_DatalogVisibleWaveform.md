# AI Assistant × Datalog：按「屏幕可见范围」喂波形给 AI

> 📚 **AI Assist 文档索引**
> | 文档 | 角色 |
> |---|---|
> | [AIAssist_Architecture.md](./AIAssist_Architecture.md) | 架构设计与规范（事实源） |
> | [AIAssist_ImplementationPlan.md](./AIAssist_ImplementationPlan.md) | 主实现计划与进度表（阶段 0~5） |
> | [AIAssist_FeatureExtension_V1.md](./AIAssist_FeatureExtension_V1.md) | 功能增补 V1（波形/控制/用量/序列/Markdown，F1~F6） |
> | **[AIAssist_DatalogVisibleWaveform.md](./AIAssist_DatalogVisibleWaveform.md)**（本文） | F1 增强：波形按「屏幕可见窗口 + Marker」喂 AI |

> 配套主文档：[AIAssist_Architecture.md](./AIAssist_Architecture.md)（架构事实源）、[AIAssist_FeatureExtension_V1.md](./AIAssist_FeatureExtension_V1.md) §1（F1 三层结构）。
> 本文定位：在 F1（波形喂 AI）基础上，把「全量喂」改为「**按 Datalog Viewer 当前 X 轴可见范围喂**」，并附带 Marker A/B 区间统计。属 **F1 增强（记作 F1.7）**。
> 分层铁律：`main.py → ui/ ←→ core/ → instruments/ → lib/`；`instruments/` 禁 Qt；`ui/` 禁阻塞 IO（QThread + Signal/Slot）；禁 `print`、异常 `exc_info=True`、禁裸 `except`。
> 状态：`☐ 待办` / `◐ 进行中` / `☑ 完成` / `⊘ 阻塞` / `— 不适用`。

---

## 0. 背景与目标

### 0.1 需求
采集 10 s（20 μs 采样率，约 50 万点/通道）后，用户在 Datalog Viewer 里放大到 `1~4 s` 全屏，再问「解读当前 Datalog 数据趋势」。

**期望**：AI 拿到的应是用户**屏幕上看到的那段（1~4 s）**，而非整段 10 s。

### 0.2 现状（已核实）
当前发给 AI 的是**完整数据**，与屏幕缩放无关：

| 环节 | 位置 | 现行为 |
|---|---|---|
| 注入回调 | [main_window.py `_provide_ai_waveform_digest`](../../ui/main_window.py) | datalog 页注入 `build_waveform_digest` |
| 构建摘要 | [n6705c_datalog_ui.py `build_waveform_digest`](../../ui/pages/n6705c_power_analyzer/n6705c_datalog_ui.py) | `build_digest(dict(self.datalog_data))` —— **全量** |
| 后台执行 | [ai_assist_panel.py `_DigestWorker.run`](../../ui/ai/ai_assist_panel.py) | 在**子线程**调用 `callback()` |
| drill-down | [query.py `get_waveform_window`](../../core/ai/actions/handlers/query.py) | 用 `deps.waveform_data_getter()` 切片，但该 getter **当前未在 `ActionDeps` 接线**，实际拿不到数据 |

### 0.3 目标（已与用户拍板）
| 决策 | 结论 |
|---|---|
| 分析范围 | **以屏幕 X 轴缩放为准**（`viewRange()[0]` 的 `[x_min, x_max]`） |
| Marker | 同时附带 Marker A/B 区间信息（时长、各通道均值等统计），不替代窗口 |
| 未缩放（看全程） | **等价全量**：可见范围 ≈ 数据全程时退回现有全量逻辑，零额外开销 |
| 性能 | **不重新采数**；只传左右时间刻度，靠等步长算术/二分定位索引切片（O(1)/O(log n)），禁 O(n) 全遍历 |
| 线程安全 | `viewRange()` 等 Qt 读取必须在 **UI 主线程**，切片/摘要在子线程 |

---

## 1. 架构总览

### 1.1 数据流（一次「解读趋势」）

```text
用户点「发送波形」或在 datalog 页提问
  │  (UI 主线程)
  ├─ ai_assist_panel._start_digest_send()
  │     ├─ range_getter()   → 取当前可见 [x0,x1]（≈全程则 None）   ← UI 线程读 Qt
  │     └─ marker_getter()  → 取 Marker A/B 位置（无则 None）        ← UI 线程读 Qt
  │
  ├─ _DigestWorker(provider_cb, x_range, marker)  (子线程，纯 Python)
  │     └─ provider_cb(x_range, marker)
  │           = main_window._provide_ai_waveform_digest(x_range, marker)
  │               = datalog_ui.build_waveform_digest(x_range, marker)
  │                   ├─ x_range=None → 现有全量 build_digest()
  │                   ├─ x_range 有值 → 快速索引切片 → build_digest(子数据)
  │                   └─ marker 有值 → 算 A→B 区间统计 → digest.marker_segment
  │
  ├─ finished(digest)  → 回 UI 线程
  └─ ai_service.send_with_waveform(text, digest)
        └─ prompt_manager.format_waveform_digest(digest)  → 注入 prompt
```

> 关键：**「读屏幕范围」与「切片+摘要」分属两个线程**。范围快照在 UI 线程取好后作为不可变参数传入子线程，子线程只碰纯 Python list，绝不触碰 Qt 对象。

### 1.2 分层归属

| 层 | 文件 | 职责 | 禁忌 |
|---|---|---|---|
| `ui/pages` | `n6705c_datalog_ui.py` | 读 `viewRange()`/Marker（UI 线程）；按窗口构建 digest | — |
| `ui/ai` | `ai_assist_panel.py` | UI 线程取范围快照 → 传子线程 worker | 子线程禁读 Qt |
| `ui` | `main_window.py` | 回调接线、补 `waveform_data_getter` | — |
| `core/ai` | `waveform_provider.py` / `schemas.py` / `prompt_manager.py` | 纯算法切片、digest 结构、prompt 文本化 | 禁 import Qt |

---

## 2. 性能方案（不重新采数）

### 2.1 现状问题
现有 [slice_window](../../core/ai/providers/waveform_provider.py) 用 `for t,v in zip(times,values): if lo<=t<=hi` —— **O(n) 全程遍历**，50 万点/通道 × 多通道在子线程也偏慢。

### 2.2 等步长快速路径（首选，O(1) 定位）
Datalog 的 `time` 为严格等步长递增（`t[i] = i * sample_period_s`，见 [n6705c_datalog_process.py](../../instruments/power/keysight/n6705c_datalog_process.py)），可直接算术定位：

```python
period = times[1] - times[0]
i0 = max(0, math.ceil((x0 - times[0]) / period))
i1 = min(len(times) - 1, math.floor((x1 - times[0]) / period))
sub_t, sub_v = times[i0:i1 + 1], values[i0:i1 + 1]   # 纯切片，零遍历
```

### 2.3 二分回退路径（O(log n)）
对导入数据 / Time Offset 后非等步长的 `time`，用 `bisect.bisect_left/right` 定位 `i0/i1`，仍远优于 O(n)。

### 2.4 窗口内再压缩
切出的窗口子数据点数可能仍上万，交给现有 `build_digest(..., max_points=...)` 做 LTTB 降采样保留形状；窗口越小细节越足（等于天然 drill-down）。

---

## 3. 数据结构变更（`core/ai/schemas.py`）

`WaveformDigest` 增 2 个可选字段（保持向后兼容，`to_dict()` 同步）：

```python
@dataclass
class WaveformDigest:
    stats: list[WaveformStat] = field(default_factory=list)
    downsampled: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    note: str = ""
    window: dict | None = None          # {"x0": 1.0, "x1": 4.0, "full": False}
    marker_segment: dict | None = None  # 见下
```

`marker_segment` 结构（A/B 都放置时才有）：

```python
{
  "a": 1.2, "b": 3.5, "duration_s": 2.3,
  "per_channel": [
    {"label": "CH1 I", "unit": "mA", "average": 11.8, "minimum": 9.1,
     "maximum": 15.2, "peak_to_peak": 6.1}
  ]
}
```

> 复用现有 `_pick_scale()` 做单位换算，保证 `marker_segment` 与 `stats` 量纲一致。

---

## 4. 接口契约（改动清单）

### 4.1 `core/ai/providers/waveform_provider.py`
- 新增 `slice_channel_fast(times, values, x0, x1) -> (sub_t, sub_v)`：等步长算术 + 二分回退。
- `slice_window()` 内部改走 `slice_channel_fast`（保持对外签名不变，drill-down 复用）。
- 新增 `build_window_digest(all_data, x0, x1, *, max_points=1500) -> WaveformDigest`：逐通道快速切片后调 `build_digest`，并填 `window`。
- 新增 `marker_segment_stats(all_data, a, b) -> dict`：A→B 区间各通道统计（同样走快速切片，纯标量输出）。

### 4.2 `core/ai/prompt_manager.py`
- [format_waveform_digest](../../core/ai/prompt_manager.py) 增补：
  - 顶部输出分析范围（`window`）：`分析范围：1.000~4.000 s（屏幕可见区）` 或 `分析范围：全程`；
  - 若有 `marker_segment`，追加 `[Marker A→B 区间]` 段：时长 + 各通道均值/峰峰。

### 4.3 `ui/pages/.../n6705c_datalog_ui.py`（UI 线程）
- 新增 `get_visible_x_range() -> tuple[float,float] | None`：
  - 读 `self.plot_widget.getPlotItem().getViewBox().viewRange()[0]`；
  - 与数据全程 `[t_min,t_max]` 求交并裁剪；
  - 可见范围覆盖率 ≥ 阈值（如 99%）→ 返回 `None`（等价全量）。
- 新增 `get_marker_window() -> dict | None`：`marker_a_pos`/`marker_b_pos` 均非空时返回 `{"a":..., "b":...}`。
- `build_waveform_digest(self, x_range=None, marker=None)`：
  - `x_range is None` → 现有全量逻辑（`window={"full": True}`）；
  - 否则 → `build_window_digest(self.datalog_data, *x_range)`；
  - `marker` 有值 → `marker_segment_stats(self.datalog_data, a, b)` 填入。
- 新增 `get_waveform_data_windowed(self) -> dict`：返回**按当前可见窗口裁剪后**的 `all_data`，供 drill-down 钳制范围。

### 4.4 `ui/ai/ai_assist_panel.py`
- 回调升级：`set_waveform_provider_callback(callback)` 中 `callback(x_range, marker) -> WaveformDigest|None`。
- 新增 `set_waveform_range_getter(getter)` / `set_waveform_marker_getter(getter)`（UI 线程同步快查）。
- [_start_digest_send](../../ui/ai/ai_assist_panel.py)：进 worker **前**在 UI 线程调 `range_getter()`/`marker_getter()` 取快照，传给 `_DigestWorker`。
- [_DigestWorker](../../ui/ai/ai_assist_panel.py)：构造接收 `x_range,marker`，`run()` 内 `provider_cb(x_range, marker)`。

### 4.5 `ui/main_window.py`
- [_provide_ai_waveform_digest](../../ui/main_window.py) 适配新签名，转发 `x_range,marker`。
- 注入 range/marker getter（仅 datalog 页）。
- 在 [ActionDeps](../../ui/main_window.py) **补全** `waveform_data_getter=self._provide_ai_waveform_windowed`，返回**窗口裁剪后**的 `all_data`，使 [get_waveform_window](../../core/ai/actions/handlers/query.py) drill-down 不越出屏幕范围。

---

## 5. 边界与降级

| 场景 | 处理 |
|---|---|
| 未缩放（看全程） | `get_visible_x_range()` 返回 `None` → 全量，零额外计算 |
| 缩放到空白无数据区 | 窗口内点数为 0 → digest 空 → 面板提示「该范围无数据」，不发空摘要 |
| 仅放置 1 个 Marker | 不算 Marker 区间，仅发窗口数据 |
| 双仪器 8 通道 / 导入文件（F1-/F2- 前缀） | 各通道按同一 `[x0,x1]` 独立切片 |
| Time Offset（仪器 B 时间已偏移） | 非等步长 → 走 `bisect` 二分路径 |
| `x0 > x1`（反向） | 切片前 `lo,hi = sorted` |
| 子线程异常 | 复用现有 `_DigestWorker.failed` → 面板降级提示 |

---

## 6. 落地计划（任务表）

> 顺序：先 core 纯算法（可单测）→ 再 ui 接线 → 最后回归。状态：`☐/◐/☑`。

| # | 任务 | 文件 | 依赖 | 状态 |
|---|---|---|---|---|
| D1 | `WaveformDigest` 增 `window`/`marker_segment` + `to_dict()` | `core/ai/schemas.py` | — | ☑ |
| D2 | `slice_channel_fast()`（等步长 + 二分回退） | `core/ai/providers/waveform_provider.py` | — | ☑ |
| D3 | `slice_window()` 改用 D2（对外签名不变） | 同上 | D2 | ☑ |
| D4 | `build_window_digest()` 逐通道切片 + 填 window | 同上 | D2,D1 | ☑ |
| D5 | `marker_segment_stats()` A→B 区间统计 | 同上 | D2,D1 | ☑ |
| D6 | `format_waveform_digest()` 输出范围 + Marker 段 | `core/ai/prompt_manager.py` | D1 | ☑ |
| D7 | `get_visible_x_range()` / `get_marker_window()` | `ui/pages/.../n6705c_datalog_ui.py` | — | ☑ |
| D8 | `build_waveform_digest(x_range,marker)` 升级 | 同上 | D4,D5,D7 | ☑ |
| D9 | `get_waveform_data_windowed()`（drill-down 数据源） | 同上 | D7 | ☑ |
| D10 | 回调升级 `callback(x_range,marker)` + range/marker getter | `ui/ai/ai_assist_panel.py` | — | ☑ |
| D11 | `_start_digest_send` UI 线程取快照 + `_DigestWorker` 透传 | 同上 | D10 | ☑ |
| D12 | `_provide_ai_waveform_digest` 适配 + 接线 getter | `ui/main_window.py` | D8,D11 | ☑ |
| D13 | `ActionDeps.waveform_data_getter` 补全（窗口裁剪源） | `ui/main_window.py` | D9 | ☑ |
| D14 | 冒烟测试 `scripts/waveform_window_test.py`（切片/一致性/边界，6 项通过） | `scripts/` | D2~D5 | ☑ |
| D15 | py_compile 全绿 + IDE 无诊断（项目未配 lint） | — | 全部 | ☑ |

### 验收标准
- ☐ 放大到 1~4 s 后提问，AI 摘要的 `点数 / min / max / 范围` 仅反映 1~4 s。
- ☐ 未缩放时行为与现状一致（全量），无明显性能回退。
- ☐ 放置 Marker A/B 后，摘要含「A→B 时长 + 各通道平均电流」。
- ☐ drill-down（`get_waveform_window`）不会返回屏幕范围外的数据。
- ☐ 50 万点 × 多通道切片在子线程完成，UI 不卡顿。
- ☐ lint 通过。

---

## 7. 同步矩阵（改完必核对）

| 对象 | 动作 |
|---|---|
| `DIRECTORY_STRUCTURE.txt` | 无新增文件，免改（仅本 md + 现有源码改动） |
| `helps/datalog.html` | 可补一句「可发送当前可见波形给 AI 助手」 |
| `.ai/memory.md` | 记录「波形喂 AI 改为按可见窗口 + Marker」决策 |
| `docs/ai/03_GOTCHAS.md` | 记「子线程禁读 Qt ViewBox；范围快照须 UI 线程取」坑点 |
| `AIAssist_FeatureExtension_V1.md` | F1 表追加 F1.7 指向本文 |
