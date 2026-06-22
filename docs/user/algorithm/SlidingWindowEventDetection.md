# 滑动窗口事件检测算法（SWED：Sliding-Window Event Detection）

> 面向功耗/电流波形的轻量级事件分段算法。核心：固定时长滑动窗口 + 增量均值 + 单调队列极值 + 双线（均值线 / 极值线）判据。
> 适用：海量原始点（数十万~数千万）单趟流式扫描，O(N) 复杂度，恒定内存，零第三方依赖。
> 实现位：`core/ai/algorithms/swed.py`（注册名 `swed`，kind=`event`）；与 STA-LTA / PELT 互补，统一经注册表 `get("swed")` 取用。

---

## 0. 一句话定义

以固定时长 `T` 的窗口沿时间轴滑动，**增量**维护窗口均值与窗口极值；**均值线**当窗口均值相对事件基线 `BASE` 突变时开 `level` 事件，**极值线**当窗口极值显著偏离均值时开 `spike`/`dip` 事件。两线平权、各自独立开关，最终按起始时间合并为同一事件列表，输出「起始时间 + 段平均值 + 峰值/谷值」。

---

## 1. 符号与输入

| 符号 | 含义 |
|---|---|
| `x[0..N-1]` | 原始采样值序列（数值单位由输入决定，见 §3.5） |
| `t[0..N-1]` | 对应时间戳（s），可等步长或非等步长 |
| `dt` | 采样间隔 = `median(diff(t))`（前若干点中位差分），采样率 `fs = 1/dt` |
| `T` | 窗口时长（s），参数 `T` |
| `W` | 窗口点数 = `max(1, round(T / dt))`；`W >= N` 时退化为 `N // 2` |
| `win` | 窗口序号（窗口左端点索引），`win = 0 .. N-W` |
| `AVG` | 当前窗口 `x[win .. win+W-1]` 的算术平均 |
| `Mn` / `Mx` | 当前窗口内的最小值 / 最大值 |
| `BASE` | 事件基线，初值为首窗均值，每个 `level` 事件结束时更新为结束处 `AVG` |

> `AVG` 以索引 `win` 为**左端点**、长度 `W` 的窗口均值；窗口每滑动 1 点 `win→win+1`。

---

## 2. 三个动态量的增量维护（核心性能来源）

### 2.1 滑动均值 AVG —— 增量 O(1)/步

维护窗口内元素和 `S`：

```
S      = x[0] + x[1] + ... + x[W-1]         # 初始化，一次 O(W)
S      = S - x[win-1] + x[win+W-1]          # 滑动一步，O(1)：减移出点、加新进点
AVG    = S / W
```

- **不重算整窗，只做一减一加**。
- **浮点累积误差**：长序列下 `S` 反复加减会累积舍入误差。对策——每滑动 `R = 2^16` 步用窗口内真实求和重算校正一次（代价可忽略，每 65536 步一次 O(W)）。

### 2.2 滑动极值 Min/Max —— 单调双端队列，摊还 O(1)/步

极值**不能**用「减移出点」做增量：若移出的点恰是当前 `Min`，无法 O(1) 得知新最小值。采用经典 **Sliding Window Minimum/Maximum**——**单调双端队列**：队列存索引，对应值单调，队首即当前极值。

**最大值队列 `Dmax`（值单调递减）**：

```
入队 i：当 Dmax 非空且 x[Dmax.back] <= x[i]，弹出队尾   # 维持递减
        Dmax.push_back(i)
过期  ：当 Dmax.front < win（已滑出左边界），弹出队首
取值  ：Mx = x[Dmax.front]
```

**最小值队列 `Dmin`（值单调递增）** 对称处理，`Mn = x[Dmin.front]`。

- 每个点最多入队 1 次、出队 1 次 → 全程 `2N` 次操作 → **摊还 O(1)/步、整体 O(N)**。
- 内存：两条队列最坏 `O(W)`，恒定上界。

---

## 3. 事件判据与双线状态机

均值线与极值线**平权、各自独立开关事件，互不绑架**：一段 RX 台阶被均值线完整覆盖（均值不回落不被打断）的同时，台阶内部的尖峰簇仍被极值线逐个独立切出。两线事件最终按 `start` 排序合并进同一 events 列表，靠 `type` 字段区分（`level` / `spike` / `dip`）。

### 3.1 睡眠门限 `sleep_floor`（单一物理闸门）

```
floor  = sleep_floor                  # 单一物理门限，无统计估计
asleep = AVG < sleep_floor            # 窗口均值低于门限即睡眠态
active = (not asleep) and (Mx >= floor or AVG >= floor)
```

睡眠态下所有判据失效（`hitA = hitB = False`），完全免疫睡眠基线微抖动。这是相对判据在睡眠段误触发（µA 级噪声 ÷ µA 级基线，相对波动轻易爆 20%/35%）的根因对策。

> **为什么用单一物理门限而非统计闸门**：统计闸门（如 MAD `med + k·mad·1.4826`）是全局统计量，会被活跃段污染、被抬高到远离物理睡眠线的水平，含义失真且不可由用户直观控制。`sleep_floor` 是用户可直接理解、直接调节的单一物理变量。

### 3.2 均值线（level）—— 判据 A：均值相对突变

```
denom_base = max(|BASE|, floor, ε)
hitA = active and |AVG - BASE| / denom_base >= theta_avg_in
```

- 抓**台阶/平台/状态切换**（RX、DVFS、负载变化）。
- `ε`（`1e-9`）防除零；与 `floor` 一起 `max(...)` 保护静默段 `AVG≈0` 时相对判据发散。
- 阈值 `theta_avg_in` 默认 `0.20`（20%）。

**level 状态机**：

```
IDLE：  冷却结束(lvl_cd==0) 且 hitA → 进入 IN_EVENT，type=level，记录 start、emax=max(AVG,BASE)
IN_EVENT：累计段均值，维护 peak/min/emax
        ev_ref   = max(emax, BASE, floor)
        fell_back = AVG <= ev_ref * (1 - theta_end)     # 相对回落
        结束 = fell_back 或 asleep
        结束 → 更新 BASE = AVG，回 IDLE，冷却 W 点
```

- 结束用**相对回落**而非绝对 floor：持续活跃平台始终高于 floor，绝对判据会让事件永不结束、被合成巨型事件；相对回落指「均值回落到事件活跃水平 `(1-theta_end)` 以下」即结束。`theta_end` 默认 `0.50`（回落超 50%），睡眠兜底为额外退出口。
- `BASE` 取上一 `level` 事件结束处均值（近似稳定段均值），避免缓慢漂移被持续误判。
- **持续稳定平台不被切碎是预期行为**：长期平稳（既不回落、相对自身也无突变）本就是一个连续 `level` 事件；平台内部精细细分交由 PELT drill-down（见 §7.4）。

### 3.3 极值线（spike/dip）—— 判据 B：极值显著偏离均值

```
denom_avg = max(|AVG|, floor, ε)
up = (Mx - AVG) / denom_avg
dn = (AVG - Mn) / denom_avg
hitB_up = (not asleep) and up >= theta_ext and Mx >= floor   → spike
hitB_dn = (not asleep) and dn >= theta_ext and Mx >= floor   → dip
ext_calm = up < theta_ext and dn < theta_ext
```

- 抓**涌流/浪涌等窄脉冲**，即使均值未明显变、极值已暴露异常。
- 阈值 `theta_ext` 默认 `0.35`（35%）。

**spike/dip 状态机**：

```
IDLE：  冷却结束(spk_cd==0) 且 (hitB_up 或 hitB_dn) → 进入 IN_EVENT，记录 start、calm=0
IN_EVENT：累计段均值，维护 peak/min/emax
        ext_calm → calm += 1，否则 calm = 0
        结束 = (calm >= calm_hold) 或 asleep         # calm_hold = max(1, W // 2)
        结束 → 回 IDLE，冷却 W 点
```

### 3.4 邻近合并

两线原始事件按 `start` 排序后做合并：**仅相邻同型 `spike`/`dip`** 且间隔 `<= merge_gap_s` 时合并为一簇（取并集区间、`peak` 取大、`min` 取小、`avg` 取两者均值）。`level` 不参与合并。

### 3.5 单位约定

算法内部不做量纲换算，数值单位由输入数据决定：

- 本项目 Datalog **内存态**数值 = 真实值 × 1000（电流 mA / 电压 mV / 功率 mW）；
- 直接导入的 CSV（如 `tests/test.csv`）为真实值（电流 A）。

因此 `sleep_floor` 的物理含义随输入量纲而定（内存态下 `0.4` ≈ 0.4 mA；真实 A 量纲下 `0.4` = 0.4 A）。调参时按当前数据量级设定，展示量纲换算统一交调用方（`waveform_provider._pick_scale` / `Event.to_dict(factor=...)`）。

---

## 4. 事件定界与收尾

- **起点**：判据命中窗口的左端点时间 `t[win]`。
- **终点**：由各自状态机的结束条件给出（level=相对回落/睡眠；spike/dip=极值平静持续 `calm_hold` 窗/睡眠）。
- **段统计**：段内累计 `AVG` 求段均值 `avg`，窗口极值滚动取 `peak`/`min`，`duration_ms = (end - start) * 1e3`。
- **扫描收尾**：主循环结束时若某线仍在 `IN_EVENT`，以末点 `t[N-1]` 强制收尾并入列。

---

## 5. 输出格式

每个事件经 `Event.to_dict(factor)` 出 JSON（`factor` 把内存值换算为展示量纲，仅作用于幅值字段）：

```json
{
  "start": 0.409068,          // 起始时间 (s)
  "end": 0.409252,            // 结束时间 (s)
  "type": "spike|level|dip",  // 触发类型：尖峰 / 电平突变 / 下陷
  "trigger": "A|B",           // 命中判据：A=均值线，B=极值线
  "avg": 8.58,                // 事件段平均值
  "peak": 16.82,              // 段峰值
  "minimum": 1.32,            // 段谷值
  "duration_ms": 0.184        // 段时长
}
```

`EventResult.info` 附算法元信息：`{algorithm, dt, W, floor, sleep_floor, raw_events}`。
`EventResult.to_index_ranges()` → `[(i0, i1), ...]` 供降采样 / 段特征消费。

---

## 6. 完整流程（伪代码，双线驱动，与实现一致）

```text
W   = max(1, round(T / dt));  若 W >= N 则 W = N // 2
S   = sum(x[0..W-1]);  Dmax, Dmin 初始化(x[0..W-1])
BASE = S / W;  R = 2^16;  calm_hold = max(1, W // 2)
lvl_state = IDLE; lvl_cd = 0
spk_state = IDLE; spk_cd = 0; spk_calm = 0

for win in 0 .. N-W:
    # ---- 增量更新（O(1) 摊还）----
    if win > 0:
        S += x[win+W-1] - x[win-1]
        deque_push(Dmax, Dmin, win+W-1); deque_expire(Dmax, Dmin, win)
    if win % R == 0 and win > 0: S = sum(x[win..win+W-1])   # 周期校正
    AVG = S / W;  Mx = x[Dmax.front];  Mn = x[Dmin.front]

    # ---- 判据（睡眠态免疫）----
    asleep = AVG < sleep_floor
    active = (not asleep) and (Mx >= floor or AVG >= floor)
    hitA   = active and |AVG - BASE| / max(|BASE|, floor, ε) >= theta_avg_in
    up = (Mx - AVG)/max(|AVG|,floor,ε);  dn = (AVG - Mn)/max(|AVG|,floor,ε)
    hitB_up = (not asleep) and up >= theta_ext and Mx >= floor
    hitB_dn = (not asleep) and dn >= theta_ext and Mx >= floor
    ext_calm = up < theta_ext and dn < theta_ext

    # ---- 均值线 ----
    if lvl_state == IDLE and lvl_cd == 0 and hitA:
        open level event; lvl_state = IN_EVENT; emax = max(AVG, BASE)
    if lvl_state == IN_EVENT:
        accumulate; emax = max(emax, AVG); ev_ref = max(emax, BASE, floor)
        if AVG <= ev_ref*(1 - theta_end) or asleep:
            close level event; BASE = AVG; lvl_state = IDLE; lvl_cd = W
    if lvl_cd > 0: lvl_cd -= 1

    # ---- 极值线 ----
    if spk_state == IDLE and spk_cd == 0 and (hitB_up or hitB_dn):
        open spike/dip event; spk_state = IN_EVENT; spk_calm = 0
    if spk_state == IN_EVENT:
        accumulate; spk_calm = (spk_calm + 1) if ext_calm else 0
        if spk_calm >= calm_hold or asleep:
            close spike/dip event; spk_state = IDLE; spk_cd = W
    if spk_cd > 0: spk_cd -= 1

# 收尾：仍在 IN_EVENT 的线以末点强制收尾
raw.sort(by start);  events = merge_adjacent_spike_dip(raw, merge_gap_s)
```

---

## 7. 复杂度与定位

### 7.1 时间复杂度

| 环节 | 单步 | 全程 |
|---|---|---|
| 滑动均值 `S` | O(1) | O(N) |
| 单调队列 Min/Max | 摊还 O(1) | O(N)（每点至多 1 入 1 出） |
| 判据 + 双线状态机 | O(1) | O(N) |
| 初始化 / 周期校正 | — | O(W) + O(N/R·W) ≈ O(N) |
| **总计** | **O(1) 摊还** | **O(N) 单趟** |

> 朴素「每窗重算 min/max」是 O(N·W)，窗口越大越爆炸；单调队列把 W 因子彻底消掉，是相对朴素实现的核心性能优势。

### 7.2 空间复杂度

| 项 | 占用 |
|---|---|
| 滑动均值 | O(1)（一个累加器） |
| 两条单调队列 | 最坏 O(W)，典型远小于 W |
| 事件列表 | O(事件数)，远小于 N |

→ **恒定附加内存**（除原始数据本身），与 N 无关。

### 7.3 实现说明

实现为**纯 Python 标量主循环**（仅 `dt` 推断借用 numpy），零额外第三方依赖，遵守 `core/` 分层铁律（禁 import Qt）。24 万点量级单趟约数百 ms；超大数据建议先按可见窗口切片再扫（见 `waveform_provider`）。

### 7.4 与 STA-LTA / PELT 的关系

| 维度 | SWED（本算法） | STA-LTA | PELT |
|---|---|---|---|
| kind | event | event | segment |
| 抓什么 | 均值突变(A) + 极值偏离(B) 通吃 | 窄尖峰/突发 | 均值台阶/平台 |
| 复杂度 | O(N) 单趟 | O(N) 单趟 | 近 O(N)，最坏 O(N²)，仅小窗启用 |
| 定位 | 轻量「一遍扫」全程总览 | 浪涌定位 | drill-down 平台细分 |

> SWED 的均值线≈PELT 的均值变点直觉、极值线≈STA-LTA 的突发直觉，**用一条 O(N) 扫描同时近似两者**；高精度段细分仍交给 PELT drill-down。

---

## 8. 已知风险与对策

| 风险 | 现象 | 对策 |
|---|---|---|
| 极值增量误解 | 「减移出点」对 min/max 不成立 | 单调队列（§2.2） |
| 浮点累积误差 | 长序列 AVG 漂移 | 每 `R=2^16` 步重算校正（§2.1） |
| 睡眠段误触发 | 睡眠基线相对判据刷屏伪事件 | 单一物理门限 `sleep_floor` + 睡眠态免疫（§3.1） |
| 活跃平台不收尾 | 绝对 floor 太低，持续平台合成巨型事件 | level 结束改「相对回落」`theta_end`（§3.2） |
| 除零爆炸 | `AVG≈0` 时相对判据发散 | `max(|·|, floor, ε)` 保护 |
| 单事件反复触发 | 持续事件每步都报 | 双线状态机 + BASE 锁定 + 冷却 `W` 点 |
| 窄事件被窗口平滑 | `W` 过大时尖峰被均值稀释 | `T` 取「比目标尖峰宽 2~4 倍」；尖峰靠极值线兜底 |
| 非等步长时间轴 | `W` 点数 ≠ 固定时长 | 用 `T/dt` 估 `W` |

---

## 9. 参数（`SwedParams`，默认值即推荐值）

| 参数 | 默认值 | 说明 |
|---|---|---|
| `T` | `2e-4`（0.2 ms） | 窗口时长，比目标脉冲宽略大，兼顾平台 |
| `theta_avg_in` | `0.20` | 均值线进入阈（判据 A，相对 BASE 突变 ≥ 20%） |
| `theta_avg_out` | `0.10` | 保留字段（当前 level 结束统一走 `theta_end`，此值未参与计算） |
| `theta_ext` | `0.35` | 极值线阈（判据 B，极值偏离均值 ≥ 35%） |
| `theta_end` | `0.50` | level 结束相对回落阈（均值回落到活跃水平 (1-θ) 以下即结束） |
| `sleep_floor` | `0.4` | 单一物理睡眠闸门 `floor=sleep_floor`；< 此值视为睡眠态免疫所有判据（量纲随输入，见 §3.5） |
| `merge_gap_s` | `2e-4`（0.2 ms） | 相邻同型 spike/dip 合并间隔 |

> 派生量（非参数）：冷却 `cooldown = W`；极值平静持续 `calm_hold = max(1, W//2)`；校正周期 `R = 2^16`。

---

## 10. 边界与正确性

- `N < 4` 或 `dt <= 0` → 返回空结果。
- `theta_*` 取 0 / `AVG=0` / 全常数序列等边界由 `max(|·|, floor, ε)` 与睡眠免疫保护，不崩。
- 极值用单调队列，结果与朴素 O(N·W) 逐窗求极值一致。
- 输出 `Event` 可序列化、token 受控（不含原始点，仅事件标量）。
