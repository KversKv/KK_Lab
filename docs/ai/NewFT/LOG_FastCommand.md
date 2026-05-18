任务：仅优化 PyQt6 串口工具 Quick Commands 区域 UI 效果

请只修改当前 PyQt6 串口工具中 Quick Commands 区域的视觉样式，不要改布局，不要改功能逻辑，不要重构数据结构。

当前 Quick Commands 区域已经有：

- 标题：⚡ Quick Commands
- 项目 Tab：lbrt、test2、test3、+
- Group 输入/选择区域
- + Group 按钮
- + Add、Import、Export 按钮
- 快捷指令按钮：test、test2

请保留现有布局和控件结构，只优化 UI 效果。

不要修改的内容：

1. 不要把 Tab 改成下拉框。
2. 不要调整整体布局结构。
3. 不要移动按钮位置。
4. 不要修改快捷指令数据结构。
5. 不要修改导入导出逻辑。
6. 不要修改串口发送逻辑。
7. 不要重构 Quick Commands 功能。
8. 不要新增复杂功能。
9. 不要改变现有控件的交互行为。

本次只做：

QSS 样式优化 + 控件视觉细节优化。

目标效果：

把当前 Quick Commands 区域优化成：

- 暗色主题更统一；
- 边框更柔和；
- Tab 更像现代工具栏标签；
- 当前选中的 Tab 更明显；
- 按钮更精致；
- 输入框更统一；
- Hover / Pressed 状态更舒服；
- 整体不要那么硬和挤；
- 视觉层次更清晰；
- 保持简洁，不要花哨。

推荐视觉风格：

整体参考：

VS Code / JetBrains / GitHub Dark

要求：

- 深色背景；
- 低对比边框；
- 蓝灰色按钮；
- 黄色标题强调；
- 当前 Tab 有明显高亮；
- Hover 有轻微反馈；
- 圆角适中，不要过大；
- 不要渐变动画；
- 不要复杂阴影。

颜色建议：

- 主背景：#020617
- 区域背景：#0f172a
- 控件背景：#111827
- 按钮背景：#1e293b
- 按钮 Hover：#334155
- 按钮 Pressed：#475569
- 边框颜色：#334155
- 边框 Hover：#475569
- 主文字：#e5e7eb
- 次级文字：#94a3b8
- 标题强调色：#fbbf24
- 选中蓝色：#2563eb
- 选中蓝色 Hover：#3b82f6
- 输入框背景：#0b1220

具体修改点：

1. Quick Commands 外层区域

给 Quick Commands 外层容器设置统一样式：

- 背景色稍微区别于主窗口；
- 边框颜色降低对比度；
- 圆角 6px 左右；
- 内部留白更舒服；
- 不要出现很硬的纯色边线。

建议效果：

background-color: #0f172a;
border: 1px solid #334155;
border-radius: 6px;

如果当前外层是 QGroupBox、QFrame 或自定义 QWidget，请给它设置 objectName，例如：

quickCommandsPanel.setObjectName("quickCommandsPanel")

然后用 QSS 单独控制。

2. 标题文字

当前标题是：

⚡ Quick Commands

请优化标题效果：

- 闪电图标和文字使用黄色强调；
- 字体稍微加粗；
- 字号不要太大；
- 和旁边 Tab 保持视觉对齐。

建议：

color: #fbbf24;
font-weight: 600;
font-size: 13px;

如果标题是 QLabel，请设置 objectName：

titleLabel.setObjectName("quickCommandsTitle")

3. Tab 样式优化

当前 Tab 看起来像普通按钮，比较生硬。

请优化现有 Tab 样式，不改变 Tab 功能。

Tab 包括：

lbrt、test2、test3、+

要求：

- 未选中 Tab 背景更暗；
- 选中 Tab 更明显；
- 选中 Tab 使用蓝色边框或蓝色底；
- Tab 之间有轻微间距；
- Tab 圆角适中；
- Hover 时有反馈；
- + Tab 保持新增入口，但样式要和其他 Tab 统一。

推荐效果：

- 未选中：深色背景 + 灰色边框；
- Hover：稍亮背景；
- 选中：蓝色背景或蓝色边框 + 白色文字。

建议 QSS：

QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background-color: #111827;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 4px 12px;
    margin-right: 4px;
    min-height: 22px;
}

QTabBar::tab:hover {
    background-color: #1e293b;
    color: #f8fafc;
    border-color: #475569;
}

QTabBar::tab:selected {
    background-color: #1d4ed8;
    color: #ffffff;
    border-color: #3b82f6;
}

QTabBar::tab:selected:hover {
    background-color: #2563eb;
}

如果当前不是 QTabWidget，而是 QPushButton 模拟的 Tab，请给这些按钮单独 objectName 或 class 属性，按按钮方式做类似样式。

4. Group Label 样式

当前：

Group:

建议让 Label 颜色弱一点，不要和按钮抢视觉。

建议：

color: #cbd5e1;
font-size: 12px;

如果是 QLabel：

groupLabel.setObjectName("quickCommandsLabel")

5. Group 输入框 / 下拉框样式

当前 Group 控件视觉比较普通。

请统一输入框 / 下拉框样式：

- 深色背景；
- 低对比边框；
- 圆角；
- 文本清晰；
- Focus 时边框变蓝；
- 高度保持 26px 左右。

适用于：

QLineEdit、QComboBox

建议 QSS：

QLineEdit,
QComboBox {
    background-color: #0b1220;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 3px 8px;
    min-height: 24px;
}

QLineEdit:hover,
QComboBox:hover {
    border-color: #475569;
}

QLineEdit:focus,
QComboBox:focus {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #e5e7eb;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

6. 普通操作按钮样式

包括：

+ Group、+ Add、Import、Export

请统一成现代暗色按钮：

- 背景为蓝灰色；
- Hover 稍亮；
- Pressed 更深或更亮；
- 圆角 5px；
- 边框柔和；
- 字体不要太粗；
- 高度统一。

建议 QSS：

QPushButton {
    background-color: #1e293b;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 4px 12px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #475569;
    border-color: #64748b;
}

QPushButton:disabled {
    background-color: #111827;
    color: #64748b;
    border-color: #1e293b;
}

7. 主要按钮差异化

当前 + Add 是主要操作按钮，建议稍微突出，但不要太亮。

如果可以设置 objectName：

addButton.setObjectName("primaryButton")

样式：

QPushButton#primaryButton {
    background-color: #1d4ed8;
    color: #ffffff;
    border: 1px solid #3b82f6;
}

QPushButton#primaryButton:hover {
    background-color: #2563eb;
}

QPushButton#primaryButton:pressed {
    background-color: #1e40af;
}

如果不想突出，也可以保持所有按钮统一。

8. Import / Export 按钮图标和文字

如果当前已经有图标，例如：

⇧ Import
⇩ Export

或者类似图标，请保持即可。

建议：

- 图标颜色和文字统一；
- 不要使用太亮的图标；
- 按钮宽度保持一致；
- Import 和 Export 视觉上同级。

如果没有图标，不强制添加。

9. 快捷指令按钮样式

当前快捷指令按钮：

test、test2

看起来比较普通。

请让它们更像快捷指令 chip / command button。

建议：

- 比普通按钮稍微小一点；
- 圆角略大一点；
- 背景深蓝灰；
- Hover 有明显反馈；
- 文字清晰；
- 不要太高。

如果可以，给快捷指令按钮设置 objectName：

cmdButton.setObjectName("quickCommandButton")

建议 QSS：

QPushButton#quickCommandButton {
    background-color: #172033;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 24px;
    min-width: 48px;
}

QPushButton#quickCommandButton:hover {
    background-color: #25344d;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton#quickCommandButton:pressed {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

10. 内边距和间距微调

不改变布局结构，但可以优化现有 spacing / margin。

建议：

layout.setContentsMargins(8, 6, 8, 8)
layout.setSpacing(6)

如果有多层 layout：

topLayout.setSpacing(6)
groupLayout.setSpacing(6)
buttonLayout.setSpacing(6)

整体不要太挤。

11. 高度统一

当前控件高度看起来不完全一致。

请尽量统一：

- Tab 高度：24px - 26px
- 输入框高度：24px - 26px
- 普通按钮高度：26px - 28px
- 快捷指令按钮高度：26px - 30px

不需要强制固定所有宽度。

12. 边框线优化

当前边框线略明显。

请避免使用太亮的边框，例如不要大量使用：

#4b5563
#64748b

普通状态建议用：

#334155

Hover 或 focus 再变亮：

#475569
#3b82f6

13. 空白区域背景

快捷指令按钮下面的空白区域目前显得比较空。

不改布局的情况下，可以让整个内容区域背景统一，不要有突兀分块。

如果有 QScrollArea：

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

建议最终视觉效果：

保持当前布局不变，但效果应类似：

⚡ Quick Commands  [ lbrt ] [ test2 ] [ test3 ] [ + ]
Group: [ 默认分组 ]  [+ Group]      [+ Add] [Import] [Export]

[ test ] [ test2 ]

但是视觉上要求：

- 外框更柔和；
- Tab 更精致；
- 选中 Tab 更明显；
- 按钮风格统一；
- Group 输入框更现代；
- 指令按钮更像快捷命令；
- Hover / Pressed 状态自然；
- 暗色主题统一。

可直接使用的 QSS 参考：

/* Quick Commands 外层 */
#quickCommandsPanel {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
}

/* 标题 */
#quickCommandsTitle {
    color: #fbbf24;
    font-weight: 600;
    font-size: 13px;
}

/* 普通文字 */
#quickCommandsPanel QLabel {
    color: #cbd5e1;
    font-size: 12px;
}

/* Tab */
#quickCommandsPanel QTabWidget::pane {
    border: none;
    background: transparent;
}

#quickCommandsPanel QTabBar::tab {
    background-color: #111827;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 4px 12px;
    margin-right: 4px;
    min-height: 22px;
}

#quickCommandsPanel QTabBar::tab:hover {
    background-color: #1e293b;
    color: #f8fafc;
    border-color: #475569;
}

#quickCommandsPanel QTabBar::tab:selected {
    background-color: #1d4ed8;
    color: #ffffff;
    border-color: #3b82f6;
}

#quickCommandsPanel QTabBar::tab:selected:hover {
    background-color: #2563eb;
}

/* 输入框和下拉框 */
#quickCommandsPanel QLineEdit,
#quickCommandsPanel QComboBox {
    background-color: #0b1220;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 3px 8px;
    min-height: 24px;
}

#quickCommandsPanel QLineEdit:hover,
#quickCommandsPanel QComboBox:hover {
    border-color: #475569;
}

#quickCommandsPanel QLineEdit:focus,
#quickCommandsPanel QComboBox:focus {
    border-color: #3b82f6;
}

#quickCommandsPanel QComboBox::drop-down {
    border: none;
    width: 20px;
}

#quickCommandsPanel QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #e5e7eb;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* 普通按钮 */
#quickCommandsPanel QPushButton {
    background-color: #1e293b;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 4px 12px;
    min-height: 24px;
}

#quickCommandsPanel QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
    color: #ffffff;
}

#quickCommandsPanel QPushButton:pressed {
    background-color: #475569;
    border-color: #64748b;
}

#quickCommandsPanel QPushButton:disabled {
    background-color: #111827;
    color: #64748b;
    border-color: #1e293b;
}

/* 主操作按钮，可选 */
#quickCommandsPanel QPushButton#primaryButton {
    background-color: #1d4ed8;
    color: #ffffff;
    border: 1px solid #3b82f6;
}

#quickCommandsPanel QPushButton#primaryButton:hover {
    background-color: #2563eb;
}

#quickCommandsPanel QPushButton#primaryButton:pressed {
    background-color: #1e40af;
}

/* 快捷指令按钮 */
#quickCommandsPanel QPushButton#quickCommandButton {
    background-color: #172033;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 24px;
    min-width: 48px;
}

#quickCommandsPanel QPushButton#quickCommandButton:hover {
    background-color: #25344d;
    border-color: #3b82f6;
    color: #ffffff;
}

#quickCommandsPanel QPushButton#quickCommandButton:pressed {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

/* 滚动区域 */
#quickCommandsPanel QScrollArea {
    background: transparent;
    border: none;
}

#quickCommandsPanel QScrollArea > QWidget > QWidget {
    background: transparent;
}

最终验收标准：

1. Quick Commands 布局和功能不变。
2. 串口发送逻辑不变。
3. Tab 仍然可以切换项目。
4. Group 仍然可以选择或显示。
5. Add、Import、Export 功能不变。
6. 快捷指令按钮仍然可以发送。
7. 视觉上比当前更统一、更现代、更精致。
8. 暗色主题下文字清晰、边框柔和、按钮有 Hover 反馈。