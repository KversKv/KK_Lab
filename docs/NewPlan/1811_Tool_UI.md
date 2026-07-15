1. Overall Layout & Architecture
The application uses a Single-Page Application (SPA) architecture occupying the full viewport height and width (100vh, 100vw).
Main Container: A flexbox column layout.
Top Header: Fixed height (56px / h-14), spans the full width.
Body Content: A flexbox row that takes up the remaining height (flex-1).
Left Area (Diagram Canvas): Expands to fill available space (flex-1), with a custom dark scrollbar for overflow.
Right Area (Property Panel): Fixed width (320px / w-80), acts as a sidebar. It is completely unmounted/hidden when no module is selected.
Overlay Level: A floating Context Menu component positioned absolutely based on cursor coordinates.
2. Global Styling & Theme
Color Palette (Dark Mode):
Backgrounds: Deep charcoal (#030712 / gray-950 for canvas), dark gray (#111827 / gray-900 for cards), and medium gray (#1f2937 / gray-800 for borders).
Accent Colors:
Emerald Green: Used for all "Active", "Selected", and "Enabled" states, as well as the main branding text.
Amber/Orange: Used to highlight the main system input bus (VSYS).
Blue: Used for secondary/nested connection branches.
Typography:
Sans-serif for general UI labels.
Monospace (e.g., JetBrains Mono, Consolas) for all technical values (Voltages, Register Addresses, Node Names).
Design Metaphor: A circuit board / node-based schematic with clean, high-contrast, rounded rectangular UI cards.
3. Component Details & Interaction Logic
A. Header
Left Side: Application Title ("KK'1811 PMU Configuration Tool") with a green CPU icon.
Right Side:
A technical readout displaying "DUT: 1811 | I2C: 0x17" in monospace.
A "Check" Button (replaces the "Connected" label). It has a translucent emerald background with a USB icon and hover-opacity transitions.
B. Diagram Canvas (Power Tree)
Main Bus (VSYS): A vertical amber line runs down the left edge, acting as the primary power source.
Routing: Nodes are laid out vertically. Horizontal lines connect the main VSYS bus to the individual modules. For modules sharing an intermediate bus (like vdd_l14_15 or sub-outputs of buck1), a parent node is drawn with vertical/horizontal branching lines (blue or dashed gray) routing to the child modules.
Module Card:
Dimensions: Fixed size (256px wide / 48px tall).
Visual State:
Default: Dark gray background with a subtle border.
Disabled: Entire card drops to 60% opacity.
Selected: Border glows emerald green, background gets a translucent green tint, and an outer green shadow is applied.
Left Slot: A small colored LED dot (Green = Enabled, Gray = Disabled) next to the Module Name.
Right Slot: A voltage stepper. Contains a - button, the current voltage (X.XXV), and a + button. Clicking +/- instantly increments/decrements the voltage by the module's defined step limit.
Hover Action: Hovering over the card reveals a small gear icon (⚙️) on the far right edge. Clicking it, or Right-Clicking anywhere on the card, opens the Context Menu.
C. Property Panel (Right Sidebar)
Header: Shows the selected Module's Name and Type (e.g., "Type: BUCK").
Status Block: An iOS-style toggle switch to Enable/Disable the output.
Mode Block: A segmented button row for selecting mode. LDOs show ['Normal', 'LP']. BUCKs show ['Normal', 'LP', 'ULP']. The active mode is highlighted in emerald green.
Voltage Control Block:
Target Input: A numeric input field (type="number") in the top right. It allows direct typing of the target voltage.
Interaction Logic: When the input loses focus (onBlur), the value is strictly clamped between the module's minVoltage and maxVoltage and rounded to two decimal places.
Slider: A horizontal <input type="range"> bound to the same voltage value. Dragging it updates the numeric input in real-time. Min/Max limits are displayed below the slider.
I2C Registers (Simulated): A read-only monospace block showing the calculated 10-bit Address (e.g., 0x1A4) and 16-bit Value (e.g., 0x80F2), which flip based on the enabled state.
Connection Info: Displays the upstream input source (e.g., Input Source: VSYS).
D. Context Menu
Appearance: A floating popover menu with a dark gray background and shadow.
Positioning: Spawns exactly at the (x, y) coordinates of the user's mouse click.
Behavior: Clicking anywhere outside the menu automatically closes it.
Contents:
A small, non-clickable header indicating the Module Name.
A full-width button to instantly toggle "Enable Output / Disable Output".
A mode selection sub-menu showing clickable rows for Normal, LP, and ULP (if BUCK), highlighting the currently active one.
4. Data Structure & State Management
To back this UI, your application state requires:
modules (Array of Objects): Each object must hold: id, name, type ('LDO' or 'BUCK'), enabled (boolean), mode (string), voltage (float), minVoltage, maxVoltage, step (float), and input (string representing the upstream parent).
selectedModuleId: A string tracking the currently clicked module to populate the Property Panel and highlight the card on the canvas.
contextMenu: An object { x, y, moduleId } tracking if the menu is open, where it is, and which module it is acting upon.


1. 电源拓扑连接关系 (Power Tree)
所有的模块输入源分为主电源（VSYS）、虚拟母线（Bus）以及级联电源。
主输入源 (VSYS)：系统的主供电轨。
直接连接到 VSYS 的单模块：
BUCK: BUCK_04, BUCK_05, BUCK_01, BUCK_02, BUCK_06, BUCK_03
LDO: LDO_01, LDO_02, LDO_06, LDO_07, LDO_08, LDO_09, LDO_10, LDO_11, LDO_03
连接到 VSYS 的母线 (Bus) 及其子模块：
vdd_l14_15 母线: 为 LDO_VMIC1, LDO_VMIC2, LDO_14, LDO_15 供电。
vdd_l5 母线: 为 LDO_13, LDO_05 供电。
级联连接 (二级供电)：
BUCK_01 的输出: 作为 LDO_12 的输入源。
2. 整体布局结构 (Layout)
应用采用 100vw * 100vh 的全屏单页无缝布局，整体采用深色主题。主要分为两大部分：
顶部导航栏 (Header)：固定在顶部，高度 56px。
主工作区 (Main Content)：占据剩余空间，分为左右两栏：
左侧画布区 (Diagram Canvas)：自适应宽度（flex-1），支持滚动。用于绘制电源拓扑图和模块卡片。
右侧属性面板 (Property Panel)：固定宽度 320px，仅在选中某个模块时展示该模块的详细信息，未选中时隐藏（或显示空白）。
3. 视觉与样式规范 (Styles)
基于 Tailwind CSS 的配色系统：
背景色: 极深灰（#030712 / gray-950）用于主背景。
卡片/面板色: 深灰（#111827 / gray-900）用于模块卡片和属性面板的输入框底色。
边框: 暗灰（#1F2937 / gray-800），所有卡片和面板都有 1px 的边框。
强调色 (Accent): 翠绿色（#10B981 / emerald-500），用于“开启”状态的指示灯、选中状态的光晕、滑块轨道以及高亮文本。
连线颜色:
VSYS 主线：琥珀色（amber-500，带透明度）。
二级/级联线：蓝色（blue-500，带透明度）。
字体: 标签和名称使用无衬线字体（Sans-serif），电压数值、寄存器地址等数据类信息使用等宽字体（Monospace，如 JetBrains Mono）。
4. 核心组件交互与逻辑 (Interaction Logic)
A. 顶部导航栏 (Header)
左侧: 芯片 Icon + 标题 "KK'1811 PMU Configuration Tool"。
右侧:
显示当前目标芯片 (DUT: 1811) 和通信地址 (I2C: 0x17)。
Check 按钮: 带有 USB Icon 的绿色按钮，具有 Hover 变色反馈，用于触发设备连接/检测状态。
B. 拓扑画布 (Diagram Canvas)
主干线绘制: 界面左侧有一条纵向的粗线代表 VSYS 母线，所有一级模块通过横向细线与此母线相连。
模块卡片 (Module Card)：
尺寸：宽 256px，高 48px，圆角矩形。
常规状态: 深灰底色，Hover 时边框变亮。
选中状态: 边框变为绿色，带有绿色发光阴影效果，提示当前属性面板正在控制该模块。
禁用状态: 整体不透明度降低至 60%。
内容布局:
最左侧：状态指示灯（开启为绿色发光，关闭为暗灰色） + 模块名称。
右侧：快捷电压调节区，包含 [-键] [当前电压值] [+键]。
悬浮反馈：鼠标移入卡片时，卡片右侧外部会滑出一个“齿轮(Settings)”小图标，提示可以右键或设置。
鼠标交互:
左键单击: 选中模块，右侧弹出/更新对应的属性面板。
右键单击: 在鼠标位置弹出 Context Menu (右键菜单)。
C. 右键菜单 (Context Menu)
跟随鼠标出现，点击外部空白处消失。
包含项:
开关切换: "Enable Output" 或 "Disable Output"。
模式切换: 列出该模块支持的模式（LDO 为 Normal/LP，BUCK 为 Normal/LP/ULP），点击直接切换。
D. 右侧属性面板 (Property Panel)
头部: 显示模块名称（带亮色图标）和模块类型（Type: LDO / BUCK）。
Status (输出控制): 仿 iOS 风格的 Toggle Switch (拨动开关)，用于控制 Enable/Disable。
Mode (模式控制): 横向排列的 Button Group。高亮显示当前选中模式。
Voltage Control (电压控制):
Target 输入框: 支持直接输入数字。带有 blur (失焦) 验证逻辑，输入超出范围的值会自动被限制（Clamp）在模块的 minVoltage 和 maxVoltage 之间。
Range Slider (滑块): 拖动滑块可实时调节电压，滑块的 step 与模块的精度一致（0.05V）。输入框与滑块双向绑定，同步更新。
底部显示该模块允许的电压下限和上限。
I2C Registers (模拟寄存器):
纯展示面板。显示 10位宽的 Address（例如 0x1A4）和 16位宽的 Value（例如 0x80F2）。此数值会随着模块的状态变化而动态改变。
Connection Info (连接信息):
显示当前模块的 Input Source（如 VSYS, VDD_L5, BUCK1 等），帮助用户明确该模块的供电来源。