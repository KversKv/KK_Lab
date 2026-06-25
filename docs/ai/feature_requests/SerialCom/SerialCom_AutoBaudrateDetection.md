你是一名资深 Python 串口工具开发工程师。请在我现有的 Python GUI 串口工具中增加“候选波特率自动匹配 / 自动重识别”功能。

## 一、功能背景

当前工具是一个 Python 构建的 GUI 串口调试工具，使用串口接收 RX 数据并显示 LOG。

现在需要增加波特率自动识别能力，但不是任意波特率识别，而是在以下固定候选波特率中进行匹配：

```python
CANDIDATE_BAUDRATES = [
    921600,
    1152000,
    2000000,
    3000000,
]
```

正常 LOG 主要是 ASCII 文本，少量情况下会主动修改设置显示 HEX 原始数据。

要求重点：

1. 可以接受真实波特率切换后有少量 RX 数据丢失；
2. 不能接受实际 RX 数据没有切换波特率，但工具误判为波特率变化，导致异常切换和额外丢数据；
3. 因此自动重识别逻辑必须保守，优先避免误切换；
4. 需要使用滑动窗口检测当前接收质量，避免：

   - 频繁误判；
   - 异常切换；
   - 长时间无法识别真实切换；
   - GUI 卡顿。

---

## 二、总体设计要求

请实现一个状态机式自动波特率检测模块，不要每个字符检测，也不要固定周期无脑扫描所有波特率。

状态机如下：

```text
UNKNOWN
  ↓
SCANNING
  ↓
LOCKED
  ↓
SUSPECT
  ↓
SCANNING
```

状态含义：

```text
UNKNOWN:
    当前未确定波特率。

SCANNING:
    在候选波特率中逐个尝试，并根据接收到的数据评分。

LOCKED:
    已经锁定某个波特率，正常接收 RX 数据。
    在此状态下绝对不要频繁扫描。

SUSPECT:
    当前波特率下连续多个滑动窗口接收质量异常，怀疑真实波特率发生变化。
    只有在异常持续成立时，才进入 SCANNING。
```

核心原则：

```text
宁可晚一点识别真实波特率变化，也不要在正常通信时误切换。
```

---

## 三、自动识别触发策略

### 1. 启动时识别

用户勾选“自动识别波特率”按钮后：

1. 暂停普通 RX 显示；
2. 依次尝试候选波特率；
3. 每个波特率读取一个短时间采样窗口；
4. 对采样数据评分；
5. 选择得分最高且超过阈值的波特率；
6. 设置串口为该波特率；
7. 进入 LOCKED 状态；
8. 恢复 RX 显示。

### 2. 运行中重识别

运行中不能周期性盲扫。

只有满足以下条件才允许进入 SUSPECT：

```text
当前 LOCKED 波特率下，连续多个滑动窗口评分低于 BAD_THRESHOLD。
```

进入 SUSPECT 后，不要立刻切换波特率，而是继续观察短暂时间。

只有满足以下条件才允许进入 SCANNING：

```text
SUSPECT 状态下，连续多个窗口仍然异常。
```

重新扫描时必须满足：

```text
新波特率得分显著高于当前波特率；
并且新波特率得分超过 LOCK_THRESHOLD；
并且同一个新波特率在连续至少 2 次检测中胜出。
```

这样避免偶发乱码、短时间噪声、HEX 数据、日志空闲等情况导致误切换。

---

## 四、建议参数

请将以下参数做成可配置项，便于后续调整：

```python
AUTO_BAUD_CONFIG = {
    "candidate_baudrates": [921600, 1152000, 2000000, 3000000],

    # 监测当前波特率接收质量的滑动窗口
    "monitor_window_min_bytes": 1024,
    "monitor_window_max_bytes": 8192,
    "monitor_window_max_time_ms": 300,

    # 扫描某个候选波特率时的采样时间
    "scan_sample_time_ms": 200,
    "scan_min_bytes": 512,
    "scan_max_bytes": 8192,

    # 切换波特率后的稳定等待时间
    "baud_switch_settle_ms": 30,

    # 当前波特率连续多少个窗口异常后进入 SUSPECT
    "bad_windows_to_suspect": 3,

    # SUSPECT 状态下连续多少个窗口仍异常后允许扫描
    "suspect_windows_to_scan": 2,

    # 新波特率需要连续胜出多少次才确认切换
    "confirm_scan_rounds": 2,

    # 防止频繁自动切换，成功切换后冷却时间
    "switch_cooldown_ms": 3000,

    # 评分阈值
    "lock_threshold": 80,
    "bad_threshold": 45,

    # 新波特率必须比当前波特率评分高出至少多少
    "switch_score_margin": 25,

    # 空闲数据处理
    "empty_window_is_bad": False,
}
```

参数解释：

- `monitor_window_max_time_ms` 不要太短，否则容易受瞬时乱码影响；
- `monitor_window_max_bytes` 不要太大，否则真实波特率变化后反应太慢；
- 对于高波特率，建议按“字节数 + 时间”共同决定窗口结束；
- 如果窗口内完全没有数据，不应默认认为波特率错误，因为设备可能只是空闲；
- 空闲窗口不应推动自动切换。

---

## 五、数据评分逻辑

因为正常 LOG 主要是 ASCII，所以请实现一个 `score_rx_data(data: bytes) -> int` 函数，返回 0~100 分。

评分目标：

```text
正常 ASCII LOG：高分
错误波特率导致的乱码：低分
空数据：特殊处理，不直接判错
HEX 原始数据：不要强行判错，但置信度应低于正常 ASCII LOG
```

建议评分逻辑如下：

### 1. 空数据

```python
if len(data) == 0:
    return None
```

注意：

- `None` 表示无有效判断；
- 不要把空数据评分为 0；
- 空数据不能直接触发 SUSPECT；
- 设备可能只是暂时没有输出。

### 2. ASCII 可打印字符比例

统计以下字符为正常字符：

```text
0x20 ~ 0x7E
\r
\n
\t
```

计算：

```python
printable_ratio = printable_count / len(data)
```

评分建议：

```text
printable_ratio >= 0.95: +45
printable_ratio >= 0.85: +35
printable_ratio >= 0.70: +20
printable_ratio >= 0.50: +5
else: +0
```

### 3. 非法控制字符惩罚

除了 `\r`、`\n`、`\t` 之外，`0x00~0x1F` 大量出现通常说明数据异常。

```text
bad_control_ratio <= 0.01: +15
bad_control_ratio <= 0.03: +8
bad_control_ratio > 0.08: -20
```

### 4. 换行结构

正常 LOG 通常有 `\n` 或 `\r\n`。

```text
存在合理换行: +15
多行且每行长度合理: +10
存在大量孤立 \r 或异常换行: -5
```

注意：

- 不要要求一定存在换行；
- 有些 LOG 可能是连续输出无换行。

### 5. 常见 LOG 字符特征

如果数据中出现常见日志字符或模式，加分：

```text
[INFO]
[WARN]
[ERROR]
DEBUG
Boot
boot
init
OK
FAIL
:
=
[
]
```

评分：

```text
存在上述任意模式: +10
存在多个模式: +15
```

### 6. UTF-8 / ASCII 解码

因为主要是 ASCII：

```text
可以严格 ASCII 解码: +10
不能 ASCII 解码但可 UTF-8 解码: +5
否则: +0
```

### 7. 长连续乱码惩罚

如果连续出现大量高位字节，例如 `>= 0x80`，或大量 `0x00`、`0xFF`，应扣分。

```text
high_bit_ratio > 0.30: -20
zero_ff_ratio > 0.20: -15
```

### 8. 最终分数

```python
score = max(0, min(100, score))
```

---

## 六、LOCKED 状态监测逻辑

请实现滑动窗口监测当前波特率是否正常。

伪代码：

```python
def on_rx_data(data: bytes):
    append_to_monitor_window(data)

    if monitor_window_ready():
        score = score_rx_data(monitor_window)

        if score is None:
            # 空闲窗口，不改变状态
            return

        if score >= bad_threshold:
            bad_window_count = 0
            suspect_window_count = 0
            state = LOCKED
        else:
            bad_window_count += 1

        if state == LOCKED and bad_window_count >= bad_windows_to_suspect:
            state = SUSPECT
            emit_status("RX quality degraded, suspect baudrate mismatch")

        clear_or_slide_monitor_window()
```

注意：

1. 只有非空窗口参与判断；
2. 偶发低分窗口不能触发扫描；
3. 必须连续多个低分窗口才进入 SUSPECT；
4. 进入 SUSPECT 后仍然不要立即切换；
5. 当前波特率如果恢复正常，应立即回到 LOCKED。

---

## 七、SUSPECT 状态逻辑

伪代码：

```python
def handle_suspect_window(data: bytes):
    score = score_rx_data(data)

    if score is None:
        return

    if score >= bad_threshold:
        # 当前波特率又恢复正常，取消怀疑
        state = LOCKED
        bad_window_count = 0
        suspect_window_count = 0
        emit_status("RX quality recovered")
        return

    suspect_window_count += 1

    if suspect_window_count >= suspect_windows_to_scan:
        state = SCANNING
        start_scan()
```

要求：

- SUSPECT 状态下仍然用当前波特率继续观察；
- 不要因为一个异常窗口就扫描；
- 避免正常 RX 中偶然出现 HEX 数据时误切换。

---

## 八、SCANNING 状态逻辑

请实现 `scan_baudrates()`。

要求：

1. 依次尝试候选波特率；
2. 对每个波特率：

   - 设置串口波特率；
   - 等待 `baud_switch_settle_ms`；
   - 读取最多 `scan_sample_time_ms`；
   - 或读到 `scan_max_bytes` 为止；
   - 至少尽量读取 `scan_min_bytes`，但不要无限等待；
   - 计算评分；
3. 保存每个候选波特率的评分；
4. 选择最高分；
5. 只有最高分超过 `lock_threshold` 才可认为有效；
6. 运行中重识别时，新波特率还必须满足：

   - 新分数比旧波特率的最近平均分高出 `switch_score_margin`；
   - 同一个新波特率连续 `confirm_scan_rounds` 次胜出；
7. 如果无法确认新波特率：

   - 回到原波特率；
   - 状态回到 LOCKED 或 SUSPECT；
   - 不要随意切换。

伪代码：

```python
def scan_baudrates(reason: str):
    results = []

    for baud in candidate_baudrates:
        serial.set_baudrate(baud)
        sleep_ms(baud_switch_settle_ms)

        data = read_sample(
            max_time_ms=scan_sample_time_ms,
            min_bytes=scan_min_bytes,
            max_bytes=scan_max_bytes,
        )

        score = score_rx_data(data)
        if score is None:
            score = 0

        results.append({
            "baudrate": baud,
            "score": score,
            "sample_len": len(data),
        })

    best = max(results, key=lambda x: x["score"])

    return best, results
```

---

## 九、运行中切换确认逻辑

为了防止误切换，请实现“双重确认”。

运行中从 LOCKED/SUSPECT 进入 SCANNING 后，不要一次扫描就立即切换。

要求：

```text
连续 confirm_scan_rounds 次扫描结果中，
相同 baudrate 都是最高分，
且分数均 >= lock_threshold，
且明显优于当前波特率，
才允许切换。
```

伪代码：

```python
def confirm_new_baudrate():
    winners = []

    for i in range(confirm_scan_rounds):
        best, results = scan_baudrates(reason="runtime_recheck")
        winners.append(best)

    if all(w["baudrate"] == winners[0]["baudrate"] for w in winners):
        candidate = winners[0]

        if candidate["score"] >= lock_threshold:
            if candidate["baudrate"] != current_baudrate:
                if candidate["score"] >= recent_current_score_avg + switch_score_margin:
                    switch_to(candidate["baudrate"])
                    return True

    restore_current_baudrate()
    return False
```

注意：

- 如果最佳波特率仍然是当前波特率，则不要记录为波特率切换；
- 如果候选波特率评分接近，不切换；
- 如果没有稳定胜出，不切换；
- 切换后进入 cooldown 时间，冷却期间禁止再次自动切换。

---

## 十、初始自动识别与运行中重识别的区别

### 初始自动识别

可以相对积极：

```text
只要某个候选波特率评分 >= lock_threshold，即可锁定。
```

但如果多个波特率评分接近，应提示用户确认。

例如：

```text
检测到多个可能波特率：
921600: 82
1152000: 79
```

此时不要强行选择，可在 GUI 上展示结果。

### 运行中重识别

必须保守：

```text
必须连续异常；
必须二次确认；
必须明显优于当前评分；
必须经过 cooldown 限制。
```

---

## 十一、GUI 要求

请在 GUI 中增加以下配置项或状态显示：

### 配置项

```text
在左侧Serial Config里面的Baudrate下面新增Auto-Detect勾选框(勾选后上面的Baudrate为禁用状态);
在设置的弹窗里面新增Auto-Detect标签, 并添加下列内容:
[ ] 启用自动波特率识别
[ ] 运行中允许自动重识别
候选波特率列表
滑动窗口大小
异常窗口阈值
锁定阈值
冷却时间
```

### 状态显示

```text
当前状态: LOCKED / SUSPECT / SCANNING
当前波特率: 921600
最近 RX 评分: 92
连续异常窗口: 0
自动切换冷却: 否
```

### 日志提示

当发生识别或切换时，在日志中插入系统提示，不要混入普通 RX 数据。

示例：

```text
[INFO] Start scanning candidate baudrates...
[INFO] 921600 score=21 sample=4096 bytes
[INFO] 1152000 score=88 sample=4096 bytes
[INFO] 2000000 score=17 sample=4096 bytes
[INFO] 3000000 score=12 sample=4096 bytes
[INFO] Locked baudrate: 1152000, score=88
```

运行中切换示例：

```text
[INFO] RX quality degraded. Enter SUSPECT state.
[INFO] Confirmed baudrate change: 1152000 -> 3000000
```

如果扫描失败：

```text
[INFO] Recheck failed. Keep current baudrate: 1152000
```

---

## 十二、线程与性能要求

串口读取和自动识别不能阻塞 GUI。

请遵守：

1. 串口读取放在后台线程或异步任务中；
2. 自动扫描过程不能卡住主线程；
3. GUI 更新通过线程安全的 signal/callback/queue 实现；
4. 读取高波特率数据时，避免逐字节处理；
5. 使用批量读取，例如每次读取 `in_waiting` 或固定 chunk；
6. 滑动窗口用 `bytearray` 或 `collections.deque`；
7. 避免频繁内存复制；
8. 扫描过程中应暂停普通 RX 展示，或者将扫描数据标记为内部检测数据，不要混入用户 LOG；
9. 如果串口关闭、拔出、设置波特率失败，要捕获异常并提示用户。

---

## 十三、串口兼容性要求

高波特率可能受 USB-UART 芯片、驱动、系统支持影响。

请在设置波特率时处理异常：

```python
try:
    serial.baudrate = baud
except Exception as e:
    mark_baudrate_unavailable(baud, e)
```

如果某个候选波特率不支持，不要崩溃，应跳过并在状态栏提示。

---

## 十四、HEX 原始数据处理要求

因为少量时候 RX 是 HEX 原始数据，所以要避免短时间 HEX 数据导致误判。

要求：

1. 如果用户当前选择“HEX 显示模式”，可以降低自动重识别敏感度；
2. HEX 模式下建议：

   - 增大 `bad_windows_to_suspect`；
   - 增大 `suspect_windows_to_scan`；
   - 或者默认禁用运行中自动重识别，只允许手动点击识别；
3. 如果 ASCII 评分低，但数据量很少，不要立即判定异常；
4. 连续多个大窗口低分才允许怀疑波特率变化。

建议：

```python
if display_mode == "HEX":
    effective_bad_windows_to_suspect = max(bad_windows_to_suspect, 5)
    effective_suspect_windows_to_scan = max(suspect_windows_to_scan, 3)
```

---

## 十五、日志完整性要求

无法保证波特率切换瞬间 RX 数据完全无损，因此请在日志中明确标记自动检测区间。

例如：

```text
[INFO] Possible baudrate mismatch, data may be lost.
[INFO] Scanning started.
[INFO] Scanning finished.
```

不要将扫描期间收到的乱码作为正常 RX LOG 输出，除非用户启用了 debug 模式。

---

## 十六、需要实现的核心类

请优先实现以下结构，具体可根据现有项目调整：

```python
class AutoBaudState:
    UNKNOWN = "UNKNOWN"
    SCANNING = "SCANNING"
    LOCKED = "LOCKED"
    SUSPECT = "SUSPECT"


class AutoBaudDetector:
    def __init__(self, serial_port, config, callbacks):
        pass

    def start_initial_scan(self):
        pass

    def stop_scan(self):
        pass

    def on_rx_data(self, data: bytes):
        pass

    def score_rx_data(self, data: bytes):
        pass

    def scan_baudrates(self, reason: str):
        pass

    def confirm_runtime_recheck(self):
        pass

    def switch_to_baudrate(self, baudrate: int):
        pass

    def restore_current_baudrate(self):
        pass

    def reset_counters(self):
        pass
```

回调建议：

```python
callbacks = {
    "on_status": callable,
    "on_score_update": callable,
    "on_state_changed": callable,
    "on_baudrate_changed": callable,
    "on_scan_result": callable,
}
```

---

## 十七、测试要求

请增加单元测试或至少提供可运行的测试函数，验证评分逻辑和状态切换逻辑。

### 测试 1：正常 ASCII LOG 高分

输入：

```python
b"[INFO] boot ok\r\n[DEBUG] init done\r\nvoltage=3.3\r\n"
```

期望：

```text
score >= 80
```

### 测试 2：乱码低分

输入：

```python
bytes([0x00, 0xFF, 0x13, 0x80, 0x91, 0x00, 0xFE] * 100)
```

期望：

```text
score <= 30
```

### 测试 3：空数据不判错

输入：

```python
b""
```

期望：

```text
score is None
```

### 测试 4：偶发异常不进入 SCANNING

连续 1~2 个坏窗口后，不能进入 SCANNING。

### 测试 5：连续异常才进入 SUSPECT

连续 `bad_windows_to_suspect` 个坏窗口后，进入 SUSPECT。

### 测试 6：SUSPECT 后恢复正常

SUSPECT 状态下，如果再次收到高分 ASCII LOG，应回到 LOCKED。

### 测试 7：运行中切换需要二次确认

一次扫描发现新波特率高分，不允许立即切换；必须连续 `confirm_scan_rounds` 次同一波特率胜出。

---

## 十八、最终目标

请基于以上要求修改或新增代码，实现一个保守、可靠、不会误切换的候选波特率自动匹配功能。

核心优先级如下：

```text
1. 避免误切换
2. 保证 GUI 不阻塞
3. 能识别真实波特率变化
4. 尽量减少切换后的数据丢失
5. 日志清晰标记检测和切换过程
```

如果某些功能与现有代码结构冲突，请优先保持现有串口收发功能稳定，然后以最小侵入方式增加自动波特率检测模块。