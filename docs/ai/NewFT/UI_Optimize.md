# KK_Lab UI 优化任务跟踪

> 基于 2026-05-21 的全面 UI 审计结果，系统性地逐步优化项目界面。
> 每个任务按优先级分阶段执行，每次会话完成 1-2 个任务。

---

## 总览

| 阶段 | 优先级 | 任务数 | 完成 | 状态 |
|------|--------|--------|------|------|
| Phase 1 | P0 - 架构级 | 4 | 4/4 | ✅ 已完成 |
| Phase 2 | P1 - 视觉体验 | 5 | 5/5 | ✅ 已完成 |
| Phase 3 | P2 - 交互精细化 | 5 | 5/5 | ✅ 已完成 |
| Phase 4 | P3 - 代码质量 | 3 | 0/3 | 🔲 未开始 |

---

## 

: P0 - 架构级优化（影响全局，必须先做）

### Task 1.1: 建立设计令牌系统 (Design Token)
- **目标**: 创建 `ui/theme.py`，集中定义所有颜色、字号、间距、圆角常量
- **详细内容**:
  - 定义颜色层级: 背景色 (bg_primary / bg_secondary / bg_card / bg_input)
  - 定义边框色层级: border_primary / border_secondary / border_accent
  - 定义文字色层级: text_primary / text_secondary / text_muted / text_accent
  - 定义语义色: success / warning / error / info
  - 定义强调色: accent_primary / accent_hover / accent_pressed
  - 定义通道色: channel_1~4 各含 accent / bg / border
  - 定义字号层级: title / subtitle / body / caption / tiny
  - 定义间距: spacing_xs(4) / sm(8) / md(12) / lg(16) / xl(24) / xxl(32)
  - 定义圆角: radius_container(16) / radius_card(12) / radius_widget(8) / radius_small(6)
- **涉及文件**: 新建 `ui/theme.py`
- **预计会话**: 会话 1
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21

### Task 1.2: 抽取通用页面样式模板
- **目标**: 建立 `ui/styles/page_styles.py`，提供 `get_page_base_qss()` 函数
- **详细内容**:
  - 汇总各页面共同的 QSS 选择器 (QLabel#pageTitle, QLabel#pageSubtitle, QFrame#panelFrame, QFrame#cardFrame 等)
  - 提供参数化接口：接受主题色/强调色作为参数
  - 包含所有状态标签样式 (statusOk / statusWarn / statusErr)
  - 包含通用控件样式 (QLineEdit, QPushButton, QCheckBox, QComboBox)
  - 保留页面特有样式的扩展能力
- **涉及文件**: 新建 `ui/styles/page_styles.py`，修改 `ui/styles/__init__.py`
- **依赖**: Task 1.1
- **预计会话**: 会话 1
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21

### Task 1.3: 提取 `_tinted_svg_icon` 为公共工具
- **目标**: 消除 4+ 处重复定义，统一为单一实现
- **详细内容**:
  - 新建 `ui/utils/icon_utils.py`（或放入现有 `ui/resource_path.py`）
  - 统一支持 DPI 感知 (`devicePixelRatio`)
  - 提供缓存机制（同路径+同色+同尺寸只渲染一次）
  - 替换所有页面中的本地 `_tinted_svg_icon` 定义为 import
- **涉及文件**:
  - 新建 `ui/utils/icon_utils.py`
  - 修改: `consumption_test.py`, `custom_test_ui.py`, `execution_logs_module_frame.py`, `serialCom_module_frame.py`
  - 额外修改: `high_low_temp_test_ui.py`, `sequence_canvas.py`
- **依赖**: 无
- **预计会话**: 会话 2
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21

### Task 1.4: SubMenu 类抽取为通用组件
- **目标**: 将 4 个几乎相同的 SubMenu 类合并为一个通用 `SidebarSubMenu`
- **详细内容**:
  - 新建 `ui/widgets/sidebar_submenu.py`
  - 接受 `menu_items: list[tuple[str, str]]` 作为参数
  - 保留 `item_clicked` Signal 和 `set_current_item()` 接口
  - 保留 hover 跟踪 (`is_hovered()`)
  - 在 MainWindow 中用 4 个实例替换 4 个类
  - 预计减少 ~450 行重复代码
- **涉及文件**:
  - 新建 `ui/widgets/sidebar_submenu.py`
  - 修改: `ui/main_window.py`
- **依赖**: Task 1.1 (使用 theme 颜色)
- **预计会话**: 会话 2
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际减少**: ~380 行 (PMUSubMenuItem + 4 SubMenu 类 → 1 通用组件)

---

## Phase 2: P1 - 视觉体验提升

### Task 2.1: 统一圆角体系
- **目标**: 全局使用 3 级圆角: 容器 16px、卡片 12px、控件 8px
- **详细内容**:
  - 从 theme.py 引用圆角常量
  - 排查并修正所有 `border-radius` 值
  - 确保 panelFrame=16px, cardFrame=12px, 按钮/输入框=8px, 小控件=6px
- **涉及文件**: 所有页面 `_setup_style()` 方法, 所有 `ui/modules/` 框架
- **依赖**: Task 1.1, Task 1.2
- **预计会话**: 会话 3
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 修正 29+ 文件中 60+ 处非标准圆角值 (18→16, 14→12, 9→8, 10→12/8, 5→6, 7→8/6)

### Task 2.2: 数值显示使用等宽字体
- **目标**: 电压/电流等跳变数值使用 Tabular 数字字体，避免 UI 抖动
- **详细内容**:
  - 为数值显示区域指定 `JetBrains Mono` 或 `Consolas` 字体
  - 在 theme.py 中定义 `FONT_MONO` 常量
  - 修改 N6705C Analyser、Consumption Test、PMU Test 等数值 QLabel
  - 确保 `font-variant-numeric: tabular-nums` 或固定宽度
- **涉及文件**: `n6705c_analyser_ui.py`, `consumption_test.py`, `pmu_isGain_ui.py`, `pmu_dcdc_efficiency.py`, `pmu_output_voltage.py`, `gpadc_test_ui.py`, `clk_test_ui.py`, `oscilloscope_base_ui.py`, `vt6002_chamber_ui.py`
- **依赖**: Task 1.1
- **预计会话**: 会话 3
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 统一所有 Consolas 引用为 FONT_MONO 常量; VT6002 gauge 使用 QFont("JetBrains Mono") + setStyleHint(Monospace)

### Task 2.3: 改善对比度（WCAG AA 合规）
- **目标**: 所有文字对比度达到 WCAG AA 标准 (4.5:1 正文, 3:1 大字)
- **详细内容**:
  - 审计所有 `color` + `background-color` 组合的对比度
  - 重点修复:
    - 导航分组标题 `#5f78a8` on `#0b1020` → 提亮至 `#7b93bf` 以上
    - `#8eb0e3` on `#0a1930` → 验证是否达标
    - 10px 字体的 muted text 需更高对比度
  - 使用在线对比度检查器验证
- **涉及文件**: `theme.py` 中 `nav_item_muted` 颜色, `main_window.py` 分组标题, `sidebar_nav_button.py`
- **依赖**: Task 1.1
- **预计会话**: 会话 4
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: nav_group_title #5f78a8 → #7b93bf (5.8:1); nav_item_muted #7f8da9 → #8fa3c2 (6.0:1); arrow #6f7d98 → #7f8fb0

### Task 2.4: 页面切换增加过渡动画
- **目标**: 用 150ms opacity 淡入替换瞬切，提升页面切换流畅感
- **详细内容**:
  - 在 `_hide_all_instrument_uis()` 和页面 show 时加入 QGraphicsOpacityEffect
  - 使用 QPropertyAnimation(opacity, 0→1, 150ms, EaseInOut)
  - 仅对主内容区域做动画，导航栏不参与
  - 注意：避免对尚未构建的页面做动画
- **涉及文件**: `ui/main_window.py`
- **依赖**: 无
- **预计会话**: 会话 4
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 新增 `_fade_in_widget()` 方法 + 所有 9 个 `_create_*_ui` 方法末尾调用

### Task 2.5: 统一间距节奏
- **目标**: 全局使用 4px 基础间距系统
- **详细内容**:
  - 从 theme.py 引用间距常量
  - 审计各页面 `setContentsMargins` / `setSpacing` 调用
  - 统一: 页面内边距 16px, 卡片内边距 12-16px, 组件间距 8-12px
  - 消除随机间距值 (如 14px, 18px, 6px 混用的情况)
- **涉及文件**: `pmu_dcdc_efficiency.py`, `pmu_isGain_ui.py`, `oscilloscope_base_ui.py`, `custom_test_ui.py`, `consumption_test.py`
- **依赖**: Task 1.1
- **预计会话**: 会话 5
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 14→12/16, 18→16, 10→8/12 统一; setContentsMargins(14,x,14,x) → (16,x,16,x)

---

## Phase 3: P2 - 交互精细化

### Task 3.1: SubMenu 展开微动画
- **目标**: 二级菜单 show 时增加 opacity + translateY 微动画
- **详细内容**:
  - 使用 QPropertyAnimation 对 submenu 的 opacity (0→1) 和 y 偏移 (+4→0) 做 100ms 动画
  - hide 时做反向 80ms 动画
  - 确保动画不影响 hover 判定逻辑
- **涉及文件**: `ui/widgets/sidebar_submenu.py` (Task 1.4 产出)
- **依赖**: Task 1.4
- **预计会话**: 会话 5
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 使用 windowOpacity + pos QPropertyAnimation; show 100ms OutCubic, hide 80ms InCubic; 重复 show 时跳过动画防抖

### Task 3.2: SubMenu 安全三角区域
- **目标**: 鼠标从导航按钮移向子菜单路径中不会意外关闭菜单
- **详细内容**:
  - 实现类似 Amazon 菜单的"安全三角"逻辑
  - 检测鼠标移动方向，如果朝向子菜单方向则延长隐藏计时
  - 可简化为: 增大延迟至 200-250ms 或检测鼠标是否在按钮→菜单的矩形区域内
- **涉及文件**: `ui/main_window.py` eventFilter 逻辑
- **依赖**: Task 1.4
- **预计会话**: 会话 6
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 隐藏延迟从 120ms → 220ms; 在 eventFilter 统一定义 _SUBMENU_HIDE_DELAY 常量

### Task 3.3: QSplitter 拖动约束
- **目标**: 限制面板最小/最大宽度，防止意外极端拖动
- **详细内容**:
  - 左侧导航栏: 固定 187px (已实现)
  - 各子页面 splitter: 设定合理 minimumWidth (左面板 ≥ 250px, 右面板 ≥ 400px)
  - Custom Test 三栏布局: 设定各栏最小宽度
- **涉及文件**: `main_window.py`, `custom_test_ui.py`, 各测试页面
- **依赖**: 无
- **预计会话**: 会话 6
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: main_window 主 splitter setCollapsible(False) + right_content minimumWidth=400; custom_test_ui canvas minimumWidth=300, property panel minimumWidth=200, vertical splitter setChildrenCollapsible(False)

### Task 3.4: 键盘导航支持
- **目标**: 为主导航增加快捷键
- **详细内容**:
  - `Ctrl+1` = N6705C, `Ctrl+2` = Oscilloscope, `Ctrl+3` = Chamber
  - `Ctrl+4` = PMU Test, `Ctrl+5` = Charger Test, `Ctrl+6` = Consumption Test
  - `Ctrl+7` = Custom Test, `Ctrl+8` = KK Serials
  - 使用 QShortcut 绑定
  - 在导航按钮 tooltip 中显示快捷键
- **涉及文件**: `ui/main_window.py`
- **依赖**: 无
- **预计会话**: 会话 7
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 新增 _setup_shortcuts() 方法; QShortcut(QKeySequence) 绑定 Ctrl+1~8; tooltip 自动追加 [Ctrl+N]

### Task 3.5: 仪器连接 Toast 通知
- **目标**: 仪器连接/断开时显示临时浮动通知
- **详细内容**:
  - 新建 `ui/widgets/toast_notification.py`
  - 支持 success / error / info 三种类型
  - 显示 2s 后自动淡出消失
  - 定位在主窗口右下角或右上角
  - 连接成功: 绿色 toast "N6705C-A Connected ✓"
  - 连接失败: 红色 toast "Connection failed: ..."
- **涉及文件**: 新建 `ui/widgets/toast_notification.py`, 修改 `main_window.py`
- **依赖**: Task 1.1 (使用 theme 颜色)
- **预计会话**: 会话 7
- **状态**: ✅ 已完成
- **完成日期**: 2026-05-21
- **实际变更**: 新建 ToastNotification 类 (windowOpacity 动画 + pos slide); 150ms fadeIn / 300ms fadeOut / 2.5s 自动消失; 集成于 _update_instrument_status() 检测新增/移除 key

---

## Phase 4: P3 - 代码质量

### Task 4.1: MainWindow 拆分
- **目标**: 将 main_window.py 从 1859 行降至 < 600 行
- **详细内容**:
  - 拆出 `ui/nav_controller.py`: 导航逻辑 + SubMenu 管理 + eventFilter
  - 拆出 `ui/instrument_status.py`: 仪器状态追踪 + 左下角显示逻辑
  - 拆出 `ui/cleanup_mixin.py`: closeEvent 中的资源释放逻辑
  - MainWindow 仅保留: 窗口初始化 + 布局创建 + 信号连接 + 页面切换
- **涉及文件**: `ui/main_window.py` → 拆分为 3-4 个文件
- **依赖**: Task 1.4 (SubMenu 已通用化后拆分更容易)
- **预计会话**: 会话 8
- **状态**: 🔲 未开始
- **完成日期**: —

### Task 4.2: 各页面迁移至设计令牌
- **目标**: 逐页将内联 QSS 替换为 theme.py + page_styles.py 的引用
- **详细内容**:
  - 按优先级顺序迁移:
    1. `consumption_test.py` (代码量最大，受益最明显)
    2. `pmu_isGain_ui.py` / `gpadc_test_ui.py`
    3. `charger_test/` 下各页面
    4. `oscilloscope_base_ui.py`
    5. `custom_test_ui.py`
  - 每个页面迁移后验证: 运行检查视觉无变化
  - 预计每会话迁移 2-3 个页面
- **涉及文件**: 所有 `ui/pages/` 下的 `_setup_style()` 方法
- **依赖**: Task 1.1, Task 1.2
- **预计会话**: 会话 9 ~ 12
- **状态**: 🔲 未开始
- **完成日期**: —

### Task 4.3: 高 DPI 适配验证与修复
- **目标**: 确保 150%/200% 缩放下图标清晰、布局不破
- **详细内容**:
  - 统一所有 `_tinted_svg_icon` 使用 devicePixelRatio (Task 1.3 已处理)
  - 验证 fixedWidth/fixedHeight 使用场景在高 DPI 下是否合理
  - 检查 `QPixmap` 渲染尺寸是否考虑 DPR
  - 测试关键页面在 Windows 150% 缩放下的表现
- **涉及文件**: `ui/utils/icon_utils.py`, 各自定义绘制组件
- **依赖**: Task 1.3
- **预计会话**: 会话 12
- **状态**: 🔲 未开始
- **完成日期**: —

---

## 会话执行计划

| 会话 | 任务 | 预计产出 |
|------|------|----------|
| 会话 1 | Task 1.1 + Task 1.2 | `ui/theme.py` + `ui/styles/page_styles.py` |
| 会话 2 | Task 1.3 + Task 1.4 | `ui/utils/icon_utils.py` + `ui/widgets/sidebar_submenu.py` + main_window 瘦身 |
| 会话 3 | Task 2.1 + Task 2.2 | 统一圆角 + 等宽数字字体 |
| 会话 4 | Task 2.3 + Task 2.4 | 对比度修复 + 页面切换动画 |
| 会话 5 | Task 2.5 + Task 3.1 | 间距统一 + SubMenu 微动画 |
| 会话 6 | Task 3.2 + Task 3.3 | 安全三角 + Splitter 约束 |
| 会话 7 | Task 3.4 + Task 3.5 | 键盘快捷键 + Toast 通知 |
| 会话 8 | Task 4.1 | MainWindow 拆分 |
| 会话 9~12 | Task 4.2 + Task 4.3 | 逐页迁移设计令牌 + DPI 验证 |

---

## 执行规则

1. **每次会话开始时**：先阅读本文档，确认当前进度和待执行任务
2. **每次会话结束时**：更新对应 Task 的状态、完成日期、涉及变更的文件列表
3. **依赖关系严格**：如 Task 标注了依赖，必须依赖项完成后才能开始
4. **向后兼容**：每个 Task 完成后，界面视觉效果应与优化前保持一致或更好，不允许引入回归
5. **测试验证**：每次修改后运行 `python main.py` 验证 UI 无崩溃，视觉无异常
6. **跑 lint**：每次会话结束前执行 lint 确认代码规范
7. **任务完成后,更新本文档;
---

## 变更日志

| 日期 | 会话 | 完成任务 | 备注 |
|------|------|----------|------|
| 2026-05-21 | 初始化 | — | 创建优化任务计划 |
| 2026-05-21 | 会话 1 | Task 1.1 + 1.2 + 1.3 + 1.4 | Phase 1 全部完成; 新建 theme.py / page_styles.py / icon_utils.py / sidebar_submenu.py; main_window.py 减少 ~380 行 |
| 2026-05-21 | 会话 2 | Task 2.1 + 2.2 + 2.3 + 2.4 + 2.5 | Phase 2 全部完成; 统一圆角体系(29+文件); 等宽数字字体(FONT_MONO); WCAG AA对比度修复; 150ms淡入动画; 间距标准化(4px基数) |
| 2026-05-21 | 会话 3 | Task 3.1 + 3.2 + 3.3 + 3.4 + 3.5 | Phase 3 全部完成; SubMenu 展开/收起微动画(opacity+translateY); 安全三角区域(220ms延迟); QSplitter约束(minimumWidth+collapsible); Ctrl+1~8键盘导航; Toast通知组件 |
