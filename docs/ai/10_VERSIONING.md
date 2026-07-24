# 10. 版本号管理规范

> 适用阶段：**研发初期（快速迭代）**。版本号与 git **完全解耦**。
> 唯一事实源：[version.py](../../version.py)。

---

## 1. 核心原则

1. **单一事实源**：版本号只在根目录 [version.py](../../version.py) 定义；其它任何地方（窗口标题、关于框、日志、spec、文件名）一律 `from version import ...` 引用，**禁止再写死版本号字符串**。
2. **与 git 解耦**：
   - 日常 `git commit` **不动**版本号；
   - **不打 tag**、**不从 git 反推**版本（不引入 `setuptools-scm` 之类）；
   - 提交多频繁都无所谓，版本号是另一条独立的、低频的人工维护线。
3. **低频手动维护**：只在"想标记一个里程碑 / 对外发包给同事试用"时，才手动改 `version.py`。

---

## 2. 版本号格式（SemVer，停在 0.x）

```
MAJOR.MINOR.PATCH      例: 0.1.0
```

研发初期主版本固定为 **`0.x`**（SemVer 约定：0.x = 尚未稳定，允许随时破坏性变更）。
等产品稳定、正式对外交付，再跳到 `1.0.0`。

### 递增规则（0.x 阶段放宽）

| 改动性质 | 版本变化 | 例 |
|---|---|---|
| 攒了一波功能、想发个包给同事试 | MINOR +1 | `0.1.0 → 0.2.0` |
| 临时修个急 bug 重新发包 | PATCH +1 | `0.1.0 → 0.1.1` |
| 日常写代码、提交 | **什么都不动** | — |

> 0.x 阶段即使有破坏性改动，也只动 MINOR，不急着上 1.0。

---

## 3. 追溯手段：构建时间戳（替代 git tag）

不打 tag，靠 `version.py` 里的 `__build__`（打包当天手填）兜底定位代码大致范围：

```python
__version__ = "0.1.0"
__build__   = "20260615"   # 打包当天手填
APP_NAME    = "KK_Lab"
```

窗口标题显示 `KK_Lab v0.1.0`，启动日志打印 `KK_Lab v0.1.0 (build 20260615) starting`。

---

## 4. 模块子版本

每个模块在自己的 `__init__.py` 顶部声明 `MODULE_VERSION`，初始全部为 `"0.0.0"`：

```python
MODULE_VERSION = "0.0.0"
```

**范围**：`ui/pages/` 下各功能页面目录 + `ui/modules/`（含子包 `serialCom_module/`）。

| 模块 | 文件 |
|---|---|
| chamber | `ui/pages/chamber/__init__.py` |
| charger_test | `ui/pages/charger_test/__init__.py` |
| consumption_test | `ui/pages/consumption_test/__init__.py` |
| custom_test | `ui/pages/custom_test/__init__.py` |
| n6705c_power_analyzer | `ui/pages/n6705c_power_analyzer/__init__.py` |
| oscilloscope | `ui/pages/oscilloscope/__init__.py` |
| pmu_test | `ui/pages/pmu_test/__init__.py` |
| vmin_hunter | `ui/pages/vmin_hunter/__init__.py` |
| modules（通用模块包） | `ui/modules/__init__.py` |
| serialCom_module | `ui/modules/serialCom_module/__init__.py` |

**递增规则**：模块单独迭代（加功能 / 修 bug）时自行 +1，**不直接牵动主版本**；与 git 同样解耦。`ui/modules/` 下的单文件模块（`*_module_frame.py`）当前不纳入。

---

## 5. 版本号的流向（引用关系）

```
version.py  (__version__ / __build__ / APP_NAME / version_string())
   │
   ├──► ui/main_window.py   窗口标题: f"{APP_NAME} v{__version__}"
   ├──► main.py 启动日志     logger.info("%s starting", version_string())
   └──► (将来) spec / 关于框  统一从 version 引用
```

---

## 6. 发布一版的动作清单

1. 改 [version.py](../../version.py) 的 `__version__`（必要时改 `__build__`）。
2. 用 spec 打包出对应 exe。
3. （可选）在 `docs/ai/memory.md` 记一句"发了 0.x.y，含哪些改动"。
4. git commit / tag **不强制**，由你按需手动决定，不与版本号绑定。
