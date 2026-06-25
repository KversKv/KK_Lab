全局字体 (Font Family)
继承了项目的全局 font-sans 设置。取决于具体环境的 Tailwind 配置，通常会优先使用系统首选无衬线字体，类似 Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto 等。
字号与字重层级 (Sizes & Weights)
按照从大到小、从主到次的层级，整个面板的文字规格大概可以分为以下 4 个梯队：
1. 标题类：14px (text-sm)
主要用于最顶层的标题或模块的标题，强调感强：
面板顶部栏 "AI Assistant"：14px (text-sm) | Bold (700) | tracking-wide (宽字符间距)
设置弹窗标题 "Settings"：14px (text-sm) | Bold (700) | tracking-wide (宽字符间距)
2. 正文与主要输入类：12px (text-xs / text-[12px])
主要用于大段阅读的内容或用户编辑区域：
聊天气泡里的消息正文：12px (text-[12px]) | Normal (400) | leading-relaxed (宽松行高，增强可读性)
底部的提问输入框：12px (text-xs) | Medium (500)
顶部小按钮 ("Clear", "Settings")：12px (text-xs) | Semibold (600)
设置弹窗中的 System Prompt 框和 Checkbox 标签：12px (text-xs) | 输入框内容是 Normal (400)，Checkbox 标签是 Bold (700)
3. 辅助操作与次级元素：11px (text-[11px])
主要用于次级的交互元素和各种建议标签，兼顾点击感但不喧宾夺主：
输入框上方的一排工具按钮 ("Select", "Analyze", "Script", "Send")：11px (text-[11px]) | Bold (700)
AI 消息框底部的 "更多选项" 下拉菜单 ("沉淀为...")：11px (text-[11px]) | Semibold (600)
空白页的快捷功能建议按钮卡片：11px (text-[11px]) | Medium (500)
设置弹窗里的一些设置标题 (System Prompt, Temperature)：11px (text-[11px]) | Bold (700)
4. 微型描述与标识：10px (text-[10px])
主要用于那些需要常驻，但绝对不能干扰用户视线的元信息：
消息发送人标识标签 ("assistant", "user")：10px (text-[10px]) | Bold (700) | uppercase (全大写) 字母间距较宽
输入区域上方的一些配置项 ("Log Level", "Max Lines")：10px (text-[10px]) | Bold (700)
模型选择下拉框选项：10px (text-[10px]) | Bold (700)
极底部的 token 用量统计 ("Usage (tokens)")：10px (text-[10px]) | Semibold (600)
设置弹窗里的温度当前数值标签 ("0.7")：10px (text-[10px]) | Bold (700)
设计总结：
整体使用了一种非常紧凑且具备极客感的文本排版策略：基础沟通的文字保持在 12px 的核心区以保证阅读，但在所有工具栏、按钮、属性标签上大量使用了极小号文字 (10px 和 11px) 配合比较重的字重（Semibold / Bold），由于字号很小，所以必须依靠高字重来保证抗锯齿的可视度，这也是大量专业生产力工具（如 IDE）最常用的布局方式。