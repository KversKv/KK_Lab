# 波形算法包（core/ai/algorithms）

> 面向功耗 / 电流 / 电压波形分析的归一化算法包。**统一输入输出契约 + 注册表**，
> 使所有波形算法可互换、可调试、可平滑新增。纯数据 + 抽象基类，**禁 import Qt**（在 `core/` 下）。

---

## 0. 一句话定位

把"事件检测 / 变点分段 / 降采样"三类波形算法收拢到同一套接口下：
- **输入**统一为 `Signal`（一次推断 `dt`，避免各算法重复造轮子）；
- **输出**统一为 `Event` / `Segment` 及其 `*Result`（`to_dict(factor)` 出 JSON，量纲换算交调用方）；
- **取用**统一经注册表 `get("名字")`，新增算法只需 `@register` 一个子类。

调用方（`waveform_provider.py` 等）只依赖契约与注册表，不关心具体算法实现。

---

## 1. 算法索引

| 名字 (name) | 类别 (kind) | 文件 | 一句话说明 | 参数 dataclass |
|---|---|---|---|---|
| `swed` | `event` | [swed.py](./swed.py) | 滑动窗口事件检测：增量均值 + 单调队列极值 + 双判据状态机 + 睡眠门限 + 相对回落 | `SwedParams` |
| `stalta` | `event` | [stalta.py](./stalta.py) | STA-LTA 能量比检测窄尖峰/突发 + MAD 绝对幅值闸门滤伪 | `StaLtaParams` |
| `pelt` | `segment` | [pelt.py](./pelt.py) | PELT 均值变点分段 + 段形态分类（spike/plateau/valley/ramp）+ 段特征 | `PeltParams` |
| LTTB / adaptive | `downsample` | [downsample.py](./downsample.py) | LTTB 保形降采样 / 事件感知非均匀降采样（函数式，非算法对象） | — |

> `kind` 取值：`event`（事件检测）/ `segment`（变点分段）/ `downsample`（降采样）。
> 用 `available(kind="event")` 列出同类算法做参数对照实验。

---

## 2. 模块结构

| 文件 | 职责 |
|---|---|
| [base.py](./base.py) | **归一化契约**：`Signal` 输入；`Event`/`Segment`/`EventResult`/`SegmentResult` 输出；`WaveformAlgorithm` 抽象基类；工具 `infer_dt`/`trapezoid`/`statistics` |
| [registry.py](./registry.py) | **注册表**：`register` 装饰器 / `get(name)` / `available(kind)` |
| [swed.py](./swed.py) | SWED 事件检测器 + `SwedParams` |
| [stalta.py](./stalta.py) | STA-LTA 事件检测器 + `StaLtaParams` + `detect_ranges_stalta`（返回索引区间） |
| [pelt.py](./pelt.py) | PELT 分段器 + `PeltParams` + `detect_change_points` / `classify_segment` / `segment_features` |
| [downsample.py](./downsample.py) | `lttb_downsample` / `adaptive_downsample`（函数式降采样） |
| [\_\_init\_\_.py](./__init__.py) | 导出契约 + 注册表 + 各算法；import 本包即触发各算法 `@register` |

---

## 3. 归一化契约（base.py）

### 3.1 输入 —— `Signal`

```python
Signal(times: list[float], values: list[float], dt: float = 0.0)
```

- `times` / `values` 同长度（长度不一致时 `times` 自动退化为索引）；
- `dt <= 0` 时自动用 `infer_dt`（前 1000 点相邻差分中位数，抗抖动）推断一次；
- `n` 属性 = 点数；`Signal.from_channel(channel)` 从 `{"time":[...], "values":[...]}` 构造。

> **单位约定**：`values` 单位由调用方决定。本项目 Datalog 内存值 = 真实值 × 1000
> （电流 mA / 电压 mV / 功率 mW）。**算法内部不做单位换算**，展示量纲换算交由调用方
> （`waveform_provider._pick_scale` / `to_dict(factor=...)`）。

### 3.2 输出 —— `Event` / `Segment`

| 输出单元 | 关键字段 |
|---|---|
| `Event` | `start`/`end`（秒）、`type`（spike/dip/level）、`trigger`、`avg`/`peak`/`minimum`、`duration_ms`、`i0`/`i1`（索引）、`extra` |
| `Segment` | `start`/`end`、`label`（spike/plateau/valley/ramp）、`mean`/`peak`/`peak_to_mean`、`width_ms`、`rise`、`charge_uAh`、`point_count` |

- `to_dict(factor=1.0)`：出 JSON；`factor` 把内存值换算为展示量纲（仅作用于幅值字段 peak/avg/minimum/mean/...）。
- 容器：`EventResult(events, info)` / `SegmentResult(segments, info)`，`info` 携带算法元信息（窗口宽度、闸门、原始事件数等）；`EventResult.to_index_ranges()` → `[(i0, i1), ...]` 供降采样/段特征消费。

### 3.3 算法基类 —— `WaveformAlgorithm`

```python
class WaveformAlgorithm(ABC):
    name: str            # 注册名，全局唯一
    kind: str            # event / segment / downsample
    params_cls: type     # 参数 dataclass

    @abstractmethod
    def run(self, signal: Signal, params=None) -> EventResult | SegmentResult: ...

    def make_params(self, **overrides):  # 默认参数 + 覆盖，便于单参扫描
        ...
```

---

## 4. 用法

### 4.1 取算法并运行

```python
from core.ai.algorithms import Signal, get

sig = Signal(times=t, values=v)              # dt 自动推断
result = get("swed").run(sig)                # → EventResult
for ev in result.events:
    print(ev.type, ev.start, ev.end, ev.peak)
payload = result.to_dict(factor=1.0)         # 出 JSON
```

### 4.2 调参 / 同类对照

```python
from core.ai.algorithms import get, available

print(available("event"))                    # ['stalta', 'swed']

algo = get("swed")
params = algo.make_params(theta_avg_in=0.30, sleep_floor=0.6)  # 覆盖默认
result = algo.run(sig, params)
```

### 4.3 新增一个算法（三步）

1. 在本目录建 `your_algo.py`，定义 `YourParams` dataclass 与 `WaveformAlgorithm` 子类；
2. 子类声明 `name` / `kind` / `params_cls`，实现 `run(signal, params) -> EventResult|SegmentResult`，并加 `@register`；
3. 在 [\_\_init\_\_.py](./__init__.py) 导入该模块（触发注册）。之后 `get("your_algo")` 即可用，与现有算法并存、可互换。

---

## 4.4 在产品里切换（AI Assistant 设置）

生产链路（`waveform_provider`）的事件检测算法由 **AI 设置** 决定，无需改代码：

1. 打开 AI Assistant 面板 → 点 **Settings** → 切到 **波形算法** 标签页；
2. **事件算法** 下拉框自动列举 `available("event")`（新增 event 算法会自动出现）；
3. 切换算法后下方动态显示该算法的常用参数（按 `params_cls` 字段生成），可改可留默认；
4. 保存后写入 `user_data/ai/config.json` 的 `ai.waveform_event_algo` / `ai.waveform_algo_params`；
5. 下次点击 **Send Waveform to AI** 即用所选算法做事件检测。

落盘字段：

```json
{
  "ai": {
    "waveform_event_algo": "swed",
    "waveform_algo_params": { "swed": { "sleep_floor": 0.6 } }
  }
}
```

`waveform_algo_params` 按算法名分桶，**仅存与默认不同的覆盖值**；切回某算法时其覆盖值仍在。
`waveform_provider.detect_event_ranges(times, values, algo=..., algo_params=...)` 是统一切换入口，
未知算法名 / 非 event 类会自动回退 `stalta` 并告警，保证调用方不中断。

---

## 5. 各算法要点

### 5.1 SWED（`swed`，事件检测）

固定时长窗口 `T` 沿时间轴滑动，**增量** O(1) 维护窗口均值（每滑动 `R=2^16` 步重算校正一次浮点误差），
**单调双端队列** 摊还 O(1) 维护窗口极值。双判据触发：

- **判据 A**（电平台阶，近 PELT）：窗口均值相对 `BASE` 突变 ≥ `theta_avg_in`；
- **判据 B**（突发尖峰，近 STA-LTA）：窗口极值偏离均值 ≥ `theta_ext`。

**睡眠门限** `floor = sleep_floor`（单一物理变量，默认 0.4mA）：`AVG < sleep_floor` 视为睡眠态，
**免疫所有判据**（µA 级抖动不误触发）。**相对回落结束** `theta_end`：均值回落到事件活跃水平
`(1 - theta_end)` 以下即结束，避免持续活跃平台（始终高于 floor）被合成巨型事件。

> 完整数学规范见 [docs/user/algorithm/SlidingWindowEventDetection.md](../../../docs/user/algorithm/SlidingWindowEventDetection.md)。

`SwedParams`：`T=2e-4` · `theta_avg_in=0.20` · `theta_avg_out=0.10` · `theta_ext=0.35` ·
`theta_end=0.50` · `sleep_floor=0.4` · `merge_gap_s=2e-4`。复杂度 O(N) 单趟、恒定内存、零第三方依赖。

### 5.2 STA-LTA（`stalta`，事件检测）

短时窗均能量 STA 与长时窗均能量 LTA 之比定位"哪里有突变"（对相对变化敏感），
再用 **MAD 绝对幅值闸门** `floor = median + mad_k·MAD·1.4826` 裁定"突变够不够大"
（绝对幅值，抗 99% 睡眠基线下 std 塌陷）。`ratio ≥ on` 触发、`≤ off` 收尾，邻近事件按 `merge_gap_s` 合并。

`StaLtaParams`：`sta_s=1e-4` · `lta_s=5e-3` · `on=4.0` · `off=1.5` · `merge_gap_s=2e-4` · `mad_k=6.0`。
依赖 numpy（向量化前缀和 O(N)）；缺 numpy 返回空结果（调用方回退）。

### 5.3 PELT（`pelt`，变点分段）

PELT（Pruned Exact Linear Time）均值变点检测，把信号切成均质段（专抓 RX / 电平 / DVFS 平台）。
自研均值代价（SSE），`auto_scale=True` 时按 BIC 把惩罚缩放为 `pen·σ²·log(n)`（σ² 取相邻差分鲁棒噪声估计），
使 `pen` 对量纲（A vs mA）鲁棒。切分后 `classify_segment` 按宽度 + 峰均比 + 均值层级贴标签，
`segment_features` 算每段均值/峰值/峰均比/宽度/上升/积分电荷(µAh)。

`PeltParams`：`pen=6.0` · `min_size=3` · `max_n=4000` · `auto_scale=True` · `factor=1.0` · `max_report=40`。
为保护性能仅对 `max_n` 内小窗启用（drill-down 子窗），整段大数据不直接跑。依赖 numpy。

### 5.4 降采样（`downsample`，函数式）

- `lttb_downsample(times, values, threshold)`：Largest-Triangle-Three-Buckets，把数百万点降到约 `threshold` 点，保留视觉峰谷；
- `adaptive_downsample(times, values, events, ...)`：事件感知非均匀降采样——平稳段 min-max 稀疏、事件段高密度保留，并产出 `density_map` 显式标注各区段采样密度（缺 numpy 或无事件时回退 LTTB）。

---

## 6. 设计约束

- **禁 Qt**：本包在 `core/` 下，仅纯 Python + 可选 numpy；UI 交互不进算法层。
- **不做单位换算**：算法只处理数值，量纲换算统一交调用方（`_pick_scale` / `to_dict(factor)`）。
- **numpy 可选**：依赖 numpy 的算法在缺失时优雅回退（返回空 / 纯 Python 路径），守打包零依赖铁律。
- **算法逻辑稳定**：迁移自 `waveform_provider.py` 的算法保持行为不变；`waveform_provider` 经薄适配委托本包，旧调用面（dict 输出 / 键名）向后兼容。
