# ui/pages/pmu — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/pages/AGENTS.md](../AGENTS.md) 硬红线。本目录为 PMU 芯片控制页的**容器**，各具体芯片页各自就近维护。

## 加载指针（AI 按需拉取）

- **PMU 1811 页（主力，独立完整模块）** → 就近读 [pmu_1811/AGENTS.md](./pmu_1811/AGENTS.md)
- **Qt / UI 通用规范** → @see [docs/ai/01_CONVENTIONS.md §6](../../../docs/ai/01_CONVENTIONS.md)
- **跨模块坑** → @see [docs/ai/03_GOTCHAS.md](../../../docs/ai/03_GOTCHAS.md)

## 本模块职责与边界

- **职责**：PMU 芯片（1811 / 1860…）的图形化配置与控制页容器。
- **上游**：`ui/main_window.py` 导航、`ui/pages/AGENTS.md`。
- **下游**：各芯片子页 `pmu_<型号>/`；芯片寄存器表 [chips/bes1811_pmu.py](../../../chips/bes1811_pmu.py)；底层经 `core/bes1811_pmu_controller.py` → `lib/i2c/`。

## 子页地图

| 子页 | 状态 | 局部指引 |
|---|---|---|
| `pmu_1811/` | ✅ 主力页（LDO/BUCK/SW 三层分离） | [pmu_1811/AGENTS.md](./pmu_1811/AGENTS.md) |
| `pmu_1860_ui.py` | 占位页（待扩展） | 本文件 |

## 局部约定

- 新增 PMU 芯片页：建 `pmu_<型号>/` 子包 + `__init__.py`（`MODULE_VERSION`），并按 `pmu_1811` 的三层（models / workers / page+widgets）结构组织。
- 各芯片页就近建自己的 `AGENTS.md`，本文件只放容器级路由与共性。
- 芯片寄存器 / 电压表统一走 `chips/`，禁止在页面层硬编码寄存器地址。
- 通过 I2C 操作芯片，UI 一律经 QThread Worker，禁主线程阻塞。

## 局部坑点

- 占位页（如 1860）无实质逻辑，改动时先确认是否要实现为完整页。
- 详见各子页 AGENTS.md；跨模块坑见 [docs/ai/03_GOTCHAS.md](../../../docs/ai/03_GOTCHAS.md)。
