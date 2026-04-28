# ADR 001 - Mock 仪器分层策略

- **状态**：Accepted
- **日期**：见 Git 历史
- **范围**：`instruments/mock/`、`instruments/factory.py`、`debug_config.py`

---

## 背景

KK_Lab 强依赖实验室仪器（N6705C、DSOX4034A、MSO64B、VT6002、CH341 I2C 适配器等）。
在以下场景没有真机：
- 研发在家 / 出差；
- UI / 业务层快速迭代；
- PR Review 验证；
- CI / 自动化冒烟。

若让 UI 代码同时处理"真机/无机"分支，会污染业务逻辑，并导致缺陷难定位。

## 决策

1. 新增全局开关 `debug_config.DEBUG_MOCK: bool`。
2. 集中在 `instruments/mock/mock_instruments.py` 提供各仪器的 `MockXxx`：
   - 接口与真实驱动**完全一致**（鸭子类型或同基类）；
   - 返回伪造但"类真实"的数据（电压 ~ 3.3V、电流随机浮动、示波器给正弦样点）。
3. `instruments/factory.py` 作为**唯一创建入口**，内部根据 `DEBUG_MOCK` 决定返回真实 / Mock 实例。
4. UI / core / 业务层**零感知** `DEBUG_MOCK`，只调 `factory.create_xxx`。

## 后果

### 优点
- 业务代码只面对一套 API。
- UI 可脱离硬件调试，迭代速度显著提升。
- 新仪器上线时自动强制补 Mock，保证开发路径闭环。

### 代价
- 每个新仪器必须同步维护 Mock（已在 Checklist 固化）。
- Mock 数据若偏离真机太远，可能掩盖真机 bug。需持续对齐。

## 反面案例（禁止）

```python
# ❌ 错误：UI 自己判断
if DEBUG_MOCK:
    inst = MockN6705C()
else:
    inst = N6705C(res)
```

```python
# ✅ 正确
from instruments.factory import create_power_analyzer
inst = create_power_analyzer(res)  # 工厂内部决定真假
```

## 相关

- [03_GOTCHAS.md #9 DEBUG_MOCK 切换](../03_GOTCHAS.md)
- [05_INSTRUMENT_GUIDE.md](../05_INSTRUMENT_GUIDE.md)
