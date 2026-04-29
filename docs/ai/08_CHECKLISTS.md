# 08 - 新功能开发 Checklist ⭐

> 在完成任务前，逐项过一遍对应 Checklist，防止漏项。

---

## ✅ 通用（每次改动都过一遍）

- [ ] 没有使用 `print()`；使用了 `log_config.get_logger(__name__)`。
- [ ] 异常带 `exc_info=True`。
- [ ] 没有裸 `except:`。
- [ ] 没有硬编码 VISA / 串口地址。
- [ ] 未在 `instruments/` 里 import 任何 `PySide6.QtWidgets`。
- [ ] 耗时 IO 未在主线程执行。
- [ ] 跨线程仅使用 Signal/Slot。
- [ ] 未主动新增 `*.md` / README（除非用户要求）。
- [ ] 未执行 `git commit`（除非用户要求）。
- [ ] 手工运行 / Mock 验证通过。

### 工程清单同步（对照 [project-rules.md §8](../../.trae/rules/project-rules.md) 同步矩阵）

- [ ] 新增 / 删除 / 重命名目录或顶层重要文件 → 已同步 [DIRECTORY_STRUCTURE.txt](../../DIRECTORY_STRUCTURE.txt)
- [ ] 新增运行时资源 / DLL / `resources/` 子目录 → 已同步 [spec/kk_lab.spec](../../spec/kk_lab.spec) 的 `datas`（必要时 `hiddenimports`）
- [ ] 新增 / 重命名功能页面 → 已同步 [helps/](../../helps/) 对应 HTML
- [ ] 源码引入新第三方包或版本变动 → 已同步 [requirements.txt](../../requirements.txt)

## ✅ 新增仪器

- [ ] 驱动文件路径正确：`instruments/<类型>/<厂商?>/<型号>.py`
- [ ] 继承 `InstrumentBase` 或 `VisaInstrument`
- [ ] 实现 `connect / disconnect / is_connected / identify`
- [ ] 在 `instruments/factory.py` 注册
- [ ] 在 `instruments/mock/mock_instruments.py` 添加 `MockXxx`
- [ ] 包 `__init__.py` 已导出
- [ ] Mock 模式下业务链路跑通
- [ ] 真机验证连接 / 核心方法
- [ ] 打包测试（若引入新 DLL / 资源）

详见：[05_INSTRUMENT_GUIDE.md](./05_INSTRUMENT_GUIDE.md)

## ✅ 新增 UI 页面

- [ ] 放在 `ui/pages/<分组>/`
- [ ] `QWidget` + 对应 Mixin（`N6705CModuleFrame`、`OscilloscopeModuleFrame`、`ChamberModuleFrame` 等）
- [ ] 复用 `ui/styles/` 里的样式常量
- [ ] 侧边栏按钮在 `main_window.py` 注册
- [ ] `QStackedWidget` 插入索引正确
- [ ] 对应 HTML 帮助放在 `helps/` 并能打开
- [ ] 仪器通过 `factory.create_*` 获取
- [ ] 业务走 `core/` + QThread
- [ ] 结果输出到 `Results/<功能>_<chip>_<时间戳>.csv`
- [ ] 关闭窗口时线程能干净退出

详见：[06_PAGE_GUIDE.md](./06_PAGE_GUIDE.md)

## ✅ 新增 UI 模组（`ui/modules/*_module_frame.py`）

- [ ] 文件放 `ui/modules/`，类名形如 `XxxConnectionMixin`
- [ ] 复用 `resources/modules/SVG_Common/` 下通用图标（search / link / unlink），不新增位图
- [ ] 搜索/连接/断开走 `QThread + QObject` 后台 Worker，绝不阻塞 UI
- [ ] 仪器实例通过 `instruments.factory.create_*` 获取（禁止直接 `new`）
- [ ] 支持 `DEBUG_MOCK` 分支，使用 `instruments.mock.mock_instruments.Mockxxx`
- [ ] 顶部 Demo 块注入 `sys.path` 兼容"直接运行"入口（见 [03_GOTCHAS.md §22](./03_GOTCHAS.md)）
- [ ] 两种启动方式均跑通：`python -m ui.modules.xxx` 与 `python ui\modules\xxx.py`
- [ ] `DIRECTORY_STRUCTURE.txt` 的 `ui/modules/` 段落同步新增条目

## ✅ 新增测试流程

- [ ] `core/test_xxx.py` 使用 `QObject + moveToThread`
- [ ] 参数 / 结果用 `dataclass`
- [ ] 支持 `start / stop / finished / progress` 至少这 4 个信号
- [ ] `finally` 中 `thread.quit(); thread.wait()`
- [ ] 异常捕获并 `emit finished(False, err)`
- [ ] 结果写入 `Results/`，含时间戳 / 芯片型号
- [ ] Mock 模式跑通
- [ ] 真机跑通

详见：[07_TEST_GUIDE.md](./07_TEST_GUIDE.md)

## ✅ 修改 / 重构现有代码

- [ ] 先阅读相关文件的上下文、导入、风格
- [ ] 分层约束未被破坏（UI 不调 VISA、驱动不依赖 UI）
- [ ] 未新增冗余注释
- [ ] 未改动与任务无关的文件
- [ ] 若动到公共 Mixin / 样式，所有受影响页面回归
- [ ] Mock 模式下 smoke test
- [ ] 若可能，真机验证

## ✅ 打包前

- [ ] `debug_config.DEBUG_MOCK = False`（除非有意发 Mock 版）
- [ ] 日志级别 `INFO` 或 `WARNING`，非 `DEBUG`
- [ ] spec 中新资源 / DLL 已加入 `datas / binaries`
- [ ] `sys._MEIPASS` 路径兼容已测
- [ ] 打包命令成功：
      `python -m PyInstaller spec/kk_lab.spec --clean --noconfirm`
- [ ] `dist/` 下产物可独立运行

## ✅ 文档沉淀

- [ ] 重要架构决策写入 `docs/ai/decisions/NNN-xxx.md`
- [ ] 会话关键上下文写入 `.ai/memory.md`
- [ ] 若新增了 lint / test 命令，更新 `02_COMMANDS.md` + `CLAUDE.md`
- [ ] 若踩坑可归纳，更新 `03_GOTCHAS.md`
