# serialCom_module — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../../AGENTS.md) 与 [ui/modules/AGENTS.md](../AGENTS.md)。**SerialCom 详细行为契约（多面板跟随 / 发送归属 / 持久化 / Save / auto-scroll / 热插拔等）在父级 ui/modules/AGENTS.md，本文件不重复展开**，只记本子包结构与局部铁律。

## 模块定位

- 串口调试控制台（KK Serial Console）：主程序内嵌 = 暗色风格；独立运行/打包 = Apple 浅色风格。
- 独立入口：`python -m ui.modules.serialCom_module.serialCom_module_frame`（frame 顶部已注入项目根 sys.path，勿删）。
- 对外仅 `SerialComMixin`（与 QWidget 组合：`class Xxx(SerialComMixin, QWidget)`），主入口 `complete_serialComWidget(parent_layout)`；`SerialSession/SerialSessionManager` 经 `__init__` 再导出（真身在 `core/serial_io/`）。
- UI 文案一律专业简洁英语。

## 文件地图

| 文件/目录 | 职责 |
|---|---|
| `serialCom_module_frame.py` | 装配薄壳：8 Mixin 多继承 + `complete_serialComWidget` + demo，**不放业务逻辑** |
| `serial_style.py` | 叶子模块：样式动态装载/导出、SVG 目录、`MODE_*`、`add_serial_port_item()`、高亮调色板 |
| `mixins/` | connection / toolbar / log_panel / filter_save / send / chart / script / persistence 八个职责 Mixin |
| `serial_log_panel.py` | **统一日志面板组件 `SerialLogPanel`**：主面板/额外内嵌面板/独立浮窗三处共用 |
| `independent_window.py` | `_IndependentSerialWindow` 独立串口浮窗 |
| `serial_hotplug.py` | `SerialPortHotplugMonitor` 模块级单例（WM_DEVICECHANGE + 去抖 + 后台重扫） |
| `widgets.py` | 可复用组件（搜索按钮 / 无边框对话框 chrome 等） |
| `dialogs/` | panel / quick_cmd / script / save / settings 对话框 |
| `controls/` | `_MiniSlideToggle`、快捷指令按钮/弹层等自定义控件 |
| `serial_chart_model/parser/controller/dialog.py` | RX 可视化：数据模型 / 规则引擎 / 控制器 / 配置与显示对话框 |
| `serialCom_dark_style.py` / `serialCom_apple_gpt5p5_style.py` | 两套主题样式表（token 真值在 `ui/styles/serial_tokens.py`） |

## 局部铁律

1. **导入方向单向**：`serial_style` ← widgets / serial_log_panel / mixins / dialogs / controls ← frame。mixin 引用对话框/控件/浮窗一律**方法内懒导入**；dialogs 禁模块级 import frame/mixins。新增懒加载子模块须同步 `spec/*` hiddenimports。
2. **禁 `import serial`**：串口 IO 全部走 `core/serial_io/`（`serial_backend` 枚举/open_serial/参数映射，`serial_session(+manager)` 会话）；脚本执行委托 `core.serial_script`。UI 禁阻塞 IO，读写走 QThread + Signal/Slot。
3. **样式切换**：`KK_SERIALCOM_STYLE` 环境变量 > 运行模式（frame 入口 / frozen `serialcom_module.exe` → light）> 默认 dark。`serial_style._is_serialcom_frame_main()` 按**入口脚本文件名**判定，勿改回 `__name__ == "__main__"`。两套样式模块必须都导出 `_SERIALCOM_STYLE_EXPORTS` 白名单符号。
4. **日志/滚动/过滤/ASCII-HEX 显示只改 `serial_log_panel.py` 一处**，禁止在 Mixin/浮窗另起平行实现；差异仅经构造参数与钩子注入。
5. **热插拔共享单例**，禁止各页面自建监控线程；串口下拉项填充统一 `serial_style.add_serial_port_item()`。
6. **关键不变量**（细节见父级）：顶部控制状态唯一经 `_sc_sync_top_control_state()` 同步；主面板发送固定 `_sc_primary_send()`；额外面板 session_id = `extra_{uid}`；持久化只恢复布局不自动回连；端口匹配一律精确 `==`。
7. 读线程三处装配（主/额外/浮窗）必须 `worker.finished → thread.quit` + `thread.finished → worker.deleteLater`。
8. **主动维护 Update Log**：凡改动串口模块功能（新增 / 修复 / 行为变更），收尾必须同步 [dialogs/settings_dialog.py](./dialogs/settings_dialog.py) 顶部 `_UPDATE_LOG_ENTRIES`（Settings → Update Log 标签页数据源），不得遗漏。格式 `(日期, 英文要点列表, 中文要点列表)`，两列表一一对应；新日期条目插在最前，同日改动并入该日期条目；要点面向用户、简洁描述变化本身，不写实现细节。

## 本地文档（按需读）

- [serialCom_module_frame.md](./serialCom_module_frame.md)：页面结构与架构说明。**注意**：行号引用为拆分前单体文件；文中 `serial_session*.py` 归属已过时（已下沉 `core/serial_io/`），结构以本文件地图为准。
- [chartVisualization.md](./chartVisualization.md)：RX 可视化图表设计说明。
