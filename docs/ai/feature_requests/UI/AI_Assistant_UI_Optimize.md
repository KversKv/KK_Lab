1. 全局调色板 (Slate/Blue Deep Theme)
界面采用高度定制的深色主题，主要色值分布如下：
基础背景层
面板主背景 / 聊天区 / 底部输入区：#070709 (Deep Surface)
Header 标题栏背景：#020617 (最深沉的背景)
任务托盘 (TaskTray) 背景：#0b1428
控件栏底层 (Controls Area)：#04060f
高亮面与卡片层
AI 气泡 / 卡片高亮面 / 任务项底色：#121629 (Elevated)
快捷指令胶囊 / 下拉菜单背景：#0f172a
边框与分割线
通用控件边框：#1e293b
输入框聚焦边框：#3b82f6
Hover 态边框 / 选中背景：#334155 / #1e293b
文字颜色
主标题 / 强调文字 (slate-200)：#e2e8f0
正文内容 (slate-300)：#cbd5e1
次要提示 / 占位符 (slate-400/500)：#94a3b8 / #64748b
强调色与状态色
发送主按钮 / 选中状态：#2563eb (Hover #1d4fd0)
拾取工具 (Inspect)：#34d399 (绿)
分析工具 (Analyze)：#3b82f6 (蓝)
草稿工具 (Script)：#818cf8 (靛)
设置对话框保存按钮：#5b3df5 (紫)
2. 核心组件尺寸与布局规范
2.1 面板框架
宽度限制：弹性宽度 240px ~ 600px，默认 360px（拖拽改变，附带 shadow-2xl 与 -ml-[1px] 处理边缘）。
Header (标题栏)：固定高度 56px (h-[56px])，水平内边距 16px (px-4)。标题字体 14px (text-[14px])，加粗 (font-bold)。
顶部按钮组：固定尺寸 28x28px (w-7 h-7)，圆角 6px (rounded-[6px])。图标尺寸 16px。Hover 时背景色为 #1e293b，图标颜色 #94a3b8。
2.2 聊天视图 (Chat View)
布局：整体内边距 16px (p-4)，消息气泡间距 20px (space-y-5)。
用户气泡 (User Bubble)：
最大宽度：88% (max-w-[88%])
背景色：#18397a，文字色：#eff6ff
圆角形状：16px，右下角尖锐化为 2px (rounded-[16px] rounded-br-[2px])
内边距：px-4 py-3，字体大小 13px，行高宽松 (leading-relaxed)。
AI 气泡 (AI Bubble)：
宽度：铺满 (w-full)
背景色：#121629，边框：1px solid #1e293b，文字色：#cbd5e1
圆角形状：16px，左下角尖锐化为 2px (rounded-[16px] rounded-bl-[2px])
动作条 (Footer)：位于气泡底部，半透明背景 #0f172a/50，包含拇指反馈按钮及更多菜单 (...)，按钮图标尺寸 12px/14px。
代码块 (Code Block)：
背景：#070709，边框：#1e293b
圆角：12px (rounded-[12px])
字体：等宽字体，大小 11px (text-[11px])。
2.3 动作确认卡片 (Action Confirm Card)
外层样式：背景 #121629，边框 #1e293b，圆角 12px。
参数框：深色内嵌背景 #070709，等宽字体。
操作按钮：固定高度 28px (h-[28px])，文字 12px，圆角 6px (rounded-[6px])。
运行 (Run)：背景 #16a34a (Hover #15803d)，文字白色。
拒绝 (Reject)：背景 #2a1414 (Hover #3f1d1d)，文字 #fca5a5。
白名单 (Allow)：背景 #0e1b33 (Hover #172a4f)，文字 #3b82f6。
2.4 底部交互区 (Compose Box & Bottom Area)
快捷指令 (Quick Row)：
胶囊形状，完全圆角 (rounded-full)。
文字 12px，内边距 px-3 py-1。
静止态：背景 #0f172a，边框 #1e293b，文字 #94a3b8。
Hover 态：背景 #1e293b，文字 #cbd5e1。
输入框容器 (Compose Box)：
背景 #070709，默认边框 #1e293b，聚焦时边框变蓝 #3b82f6。
圆角 12px (rounded-[12px])。
弹性输入区 (Input Area)：
高度弹性约束：最小高度 80px (minHeight: "80px" / h-20)，最高延伸至 160px (max-h-[160px])，超出滚动。
字体 13px，颜色 #e2e8f0，占位符颜色 #64748b。
工具栏与配置行 (Controls Area)：
顶部带 1px solid #1e293b 边框，背景色略深为 #04060f。
Range 行：下拉菜单高度小，文字 11px。
Action 行 (工具图标)：尺寸 28x28px，图标 16px，Hover 背景 #1e293b。
Send 按钮：微动效按钮，按下缩放 95% (active:scale-95)。高度 28px，背景 #2563eb。
2.5 弹出层设置对话框 (Settings Dialog)
遮罩层：bg-black/60 加背景模糊 (backdrop-blur-sm)。
主面板：最大宽度限制 (max-w-sm)，背景 #070709，圆角 xl，边框 #1e293b。
表单输入：文字 12px，内边距 px-3 py-2，边框 #1e293b，获得焦点时边框变为主蓝色 #3b82f6。
3. 微交互与视觉动效 (Micro-interactions)
面板拖拽 (Resize)：边缘设置 w-1 cursor-col-resize 触控区，拖拽时赋予 hover:bg-[#3b82f6] active:bg-[#3b82f6] 高亮反馈。
Send 发送缩放：按键自带 active:scale-95 transition-all 产生物理按压反馈。
折叠/展开动画：任务托盘展开与闭合配合 ChevronDown 和 ChevronRight 切换。
焦点环流动：输入框外层容器监听 Focus 状态改变整个框的 Border 颜色，实现统一的发光效果，而非局限于内部的 textarea。