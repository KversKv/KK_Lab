# 07 - 新增测试功能指南

本文档聚焦 **"如何在 core/ 层新增一个自动化测试流程"**，配合新 UI 页面一起落地。

---

## 1. 测试功能 = UI + Core + 仪器三件套

```
┌────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│ ui/pages/xxx/  │  ───▶  │ core/test_xxx.py│  ───▶  │ instruments/... │
│ 参数 / 展示     │        │ 流程编排 / 线程  │        │ 仪器驱动         │
└────────────────┘  ◀───  └─────────────────┘  ◀───  └─────────────────┘
        Signal/Slot             Signal/Slot
```

## 2. 新增步骤

### Step 1：定义数据结构

使用 `dataclass` 描述测试参数 / 单次结果：

```python
# core/test_xxx.py
from dataclasses import dataclass

@dataclass
class FreqResponseParams:
    chip: str
    channel: int
    freqs_hz: list[float]
    vbat_v: float

@dataclass
class FreqResponsePoint:
    freq_hz: float
    gain_db: float
    phase_deg: float
```

### Step 2：实现测试类（QThread 模式）

```python
from PySide6.QtCore import QObject, QThread, Signal
from log_config import get_logger
from instruments.factory import create_power_analyzer, create_oscilloscope

logger = get_logger(__name__)


class FreqResponseTest(QObject):
    progress = Signal(int)                    # 0~100
    point_ready = Signal(object)              # FreqResponsePoint
    finished = Signal(bool, str)              # success, message

    def __init__(self, params: FreqResponseParams, n6705c, scope):
        super().__init__()
        self._params = params
        self._n6705c = n6705c
        self._scope = scope
        self._abort = False

    def start(self):
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()

    def stop(self):
        self._abort = True

    def _run(self):
        try:
            n = len(self._params.freqs_hz)
            for i, f in enumerate(self._params.freqs_hz):
                if self._abort:
                    break
                # 1. 设置激励源
                self._n6705c.set_voltage(1, self._params.vbat_v)
                # 2. 示波器读响应
                gain = self._scope.measure_amplitude(1)
                # 3. emit 单点
                self.point_ready.emit(FreqResponsePoint(f, gain, 0.0))
                self.progress.emit(int((i + 1) * 100 / n))
            self.finished.emit(True, "完成")
        except Exception as e:
            logger.error("FreqResponseTest failed: %s", e, exc_info=True)
            self.finished.emit(False, str(e))
        finally:
            self._thread.quit()
            self._thread.wait()
```

### Step 3：UI 层订阅

```python
self._test = FreqResponseTest(params, n6705c, scope)
self._test.progress.connect(self.progress_bar.setValue)
self._test.point_ready.connect(self._on_point)
self._test.finished.connect(self._on_finished)
self._test.start()
```

### Step 4：结果落盘

```python
import csv, os, datetime
def _save_results(points, chip):
    os.makedirs("Results", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"Results/freq_response_{chip}_{ts}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["freq_hz", "gain_db", "phase_deg"])
        for p in points:
            w.writerow([p.freq_hz, p.gain_db, p.phase_deg])
    logger.info("Results saved: %s", path)
```

### Step 5：Mock 验证

1. `debug_config.DEBUG_MOCK = True`；
2. `Mock` 仪器返回固定 / 随机数据；
3. 全流程跑一遍，确保 UI 响应、进度、文件输出正确。

### Step 6：真机验证

- 切回 `DEBUG_MOCK = False`；
- 连接真实硬件；
- 记录耗时、异常场景；
- 调整超时 / 重试。

## 3. 线程模型 & 停止

- **禁止**继承 `QThread` 再 override `run`；项目习惯 `QObject + moveToThread`。
- 停止信号通过 `self._abort = True` 软停止，子线程下一轮循环检测。
- 强制停止的场景（仪器长阻塞）需在驱动层支持超时。

## 4. 芯片配置使用

若新测试需要读取芯片参数（寄存器地址、默认电压），走 `chips/bes_chip_configs/`：

```python
from chips.bes_chip_configs.main_chips.bes1307p import BES1307P_Config
cfg = BES1307P_Config()
vbat_default = cfg.pmu.vbat_default
```

## 5. Checklist

- [ ] 参数 / 结果使用 `dataclass`
- [ ] 测试类放在 `core/`，无 Qt Widget 依赖
- [ ] 使用 `QObject + moveToThread`
- [ ] 有 `start` / `stop` / `finished` 信号
- [ ] 全流程异常被捕获 + 日志 + `finished(False, ...)`
- [ ] 结果输出到 `Results/` + 时间戳命名
- [ ] 与 UI 交互只用 Signal/Slot
- [ ] Mock 模式可跑通
- [ ] 配套 HTML 帮助已添加

## 6. 反模式

- ❌ `time.sleep(...)` 塞在主线程；
- ❌ `while not done:` 忙等；
- ❌ 子线程直接 `self.ui_widget.setText(...)`；
- ❌ 读写同一仪器从两个线程不加锁；
- ❌ 忘记在 `finally` 里 `self._thread.quit(); wait()`。
