# 05 - 新增仪器驱动指南

本文档描述如何向 `instruments/` 添加一款新仪器（示波器、电源、温箱、适配器等）。

---

## 1. 决策树

```
新仪器属于哪一类？
├── 示波器       → instruments/scopes/<厂商>/<型号>.py
├── 电源分析仪   → instruments/power/<厂商>/<型号>.py
├── 温箱 / 负载  → instruments/chambers/<型号>.py
└── 通信适配器   → instruments/adapters/<型号>.py
```

## 2. 步骤清单

### 步骤 1：确认通信方式

| 通信方式 | 基类 |
|---|---|
| VISA（USB / GPIB / TCPIP / Serial-VISA） | 继承 [VisaInstrument](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/base/visa_instrument.py) |
| 原生 pyserial / Modbus | 直接继承 [InstrumentBase](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/base/instrument_base.py) |
| USB-HID / 自定义 DLL | 继承 `InstrumentBase`，实现读写 |

### 步骤 2：创建驱动文件

例：新增 Tektronix `MSO5` 示波器。

```
instruments/scopes/tektronix/mso5.py
```

骨架：

```python
from instruments.scopes.base import OscilloscopeBase
from log_config import get_logger

logger = get_logger(__name__)


class MSO5(OscilloscopeBase):
    def __init__(self, resource: str):
        super().__init__(resource)
        self._idn = None

    def connect(self) -> bool:
        try:
            self._open_visa()
            self._idn = self.query("*IDN?").strip()
            logger.info("MSO5 connected: %s", self._idn)
            return True
        except Exception as e:
            logger.error("MSO5 connect failed: %s", e, exc_info=True)
            return False

    def disconnect(self):
        self._close_visa()

    def is_connected(self) -> bool:
        return self._visa is not None

    def identify(self) -> str:
        return self._idn or ""

    # —— 业务接口 ——
    def measure_voltage(self, channel: int) -> float:
        return float(self.query(f"MEASU:IMM:SOURCE CH{channel}; MEASU:IMM:VAL?"))

    def capture_screen(self, path: str):
        ...
```

### 步骤 3：更新工厂

在 [instruments/factory.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/factory.py) 里注册：

```python
from instruments.scopes.tektronix.mso5 import MSO5

def create_oscilloscope(osc_type: str, resource: str):
    if osc_type == "dsox4034a":
        return DSOX4034A(resource)
    elif osc_type == "mso64b":
        return MSO64B(resource)
    elif osc_type == "mso5":
        return MSO5(resource)
    else:
        raise ValueError(f"Unknown oscilloscope type: {osc_type}")
```

如果希望 `DEBUG_MOCK` 时自动替换：

```python
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockMSO5

def create_oscilloscope(osc_type: str, resource: str):
    if DEBUG_MOCK:
        return MockMSO5(resource)
    ...
```

### 步骤 4：补充 Mock（强制）

在 [instruments/mock/mock_instruments.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/instruments/mock/mock_instruments.py) 添加：

```python
class MockMSO5:
    def __init__(self, resource: str):
        self.resource = resource
    def connect(self): return True
    def disconnect(self): pass
    def is_connected(self): return True
    def identify(self): return "MOCK MSO5"
    def measure_voltage(self, channel): return 3.3
    def capture_screen(self, path): ...
```

### 步骤 5：注册到包 `__init__.py`

在 `instruments/scopes/tektronix/__init__.py` 暴露：

```python
from .mso5 import MSO5
__all__ = ["MSO64B", "MSO5"]
```

### 步骤 6：UI 层自动识别（可选）

若新示波器希望在 `oscilloscope_base_ui.py` 的自动识别流程中出现，需：
1. 在自动识别逻辑中匹配 `*IDN?` 返回关键字；
2. 根据型号实例化对应驱动。

### 步骤 7：跑通 Mock

```powershell
# debug_config.py 设 DEBUG_MOCK = True
python main.py
```

验证新仪器在 Mock 下能 "搜索 → 连接 → 调用业务方法" 全链路跑通。

### 步骤 8：真机联调

- 切换 `DEBUG_MOCK = False`；
- 使用 `pyvisa.ResourceManager().list_resources()` 找到设备；
- 记录异常、完善超时。

### 步骤 9：打包清单

若新增 DLL / 资源：
1. 在 `spec/kk_lab.spec` 的 `datas`/`binaries` 声明；
2. 路径加载用 `sys._MEIPASS`；
3. 打包后测试能在 `dist/` 运行。

## 3. 检查清单（Checklist）

- [ ] 驱动继承了正确基类
- [ ] `connect / disconnect / is_connected / identify` 完整
- [ ] 仪器层**没有**引入任何 Qt Widget
- [ ] 所有异常都 `logger.error(..., exc_info=True)`
- [ ] 工厂 `create_xxx` 注册完成
- [ ] `MockXxx` 已同步添加
- [ ] `__init__.py` 导出
- [ ] Mock 模式能完整跑流程
- [ ] 真机连接验证通过
- [ ] 打包（若引入新依赖 / DLL）通过

## 4. 反模式（禁止）

- ❌ 在仪器类里 `from PySide6.QtWidgets import ...`
- ❌ 在仪器类里 `print()`
- ❌ 在仪器类里硬编码 VISA 资源
- ❌ 忘记写 Mock 类
- ❌ `except: pass` 吞异常
