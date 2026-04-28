# ADR 002 - 示波器自动识别策略

- **状态**：Accepted
- **日期**：见 Git 历史
- **范围**：`ui/pages/oscilloscope/oscilloscope_base_ui.py`、`instruments/factory.py`、`instruments/scopes/`

---

## 背景

实验室存在多品牌示波器：Keysight DSOX4034A、Tektronix MSO64B（未来可能加入 MSO5 等）。
早期方案为"每种示波器一个独立页面"，存在问题：
- 侧边栏多处示波器入口，用户易混淆；
- 连接、截图、测量逻辑重复；
- 新增型号要新增一整个页面。

## 决策

1. **统一 UI 页面**：`ui/pages/oscilloscope/oscilloscope_base_ui.py` 作为唯一示波器入口。
2. **自动识别型号**：
   - 用户在 Mixin 搜索得到 VISA 资源后，UI 通过 `*IDN?` 查询；
   - 根据 IDN 字符串关键字（`KEYSIGHT,DSO-X`、`TEKTRONIX,MSO`）分派型号；
   - 调用 `instruments.factory.create_oscilloscope("<type>", resource)` 创建实例。
3. **公共接口抽象**：`instruments/scopes/base.py` 定义示波器基类；页面只依赖基类 API。

## 后果

### 优点
- 用户视角"一个示波器页面"，自适应硬件；
- 新型号只需：
  1. 实现驱动继承 `OscilloscopeBase`；
  2. 在 `factory` 注册；
  3. 在 UI 自动识别逻辑中追加一条关键字匹配。
- 测量 / 截图 / 触发 / 反相等通用逻辑零重复。

### 代价
- 基类必须"最小公约数"设计；品牌独有特性要谨慎暴露。
- IDN 字符串匹配需要维护关键字白名单。

## 自动识别伪代码

```python
idn = tmp_visa.query("*IDN?").upper()
if "KEYSIGHT" in idn and "DSO-X" in idn:
    osc_type = "dsox4034a"
elif "TEKTRONIX" in idn and "MSO" in idn:
    osc_type = "mso64b"
else:
    raise ValueError(f"Unsupported oscilloscope: {idn}")

scope = create_oscilloscope(osc_type, resource)
```

## 相关

- [04_ARCHITECTURE.md §3.7](../04_ARCHITECTURE.md)
- [05_INSTRUMENT_GUIDE.md](../05_INSTRUMENT_GUIDE.md)
- [06_PAGE_GUIDE.md](../06_PAGE_GUIDE.md)
