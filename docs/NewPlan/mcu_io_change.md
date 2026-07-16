一、 整体结构与响应式布局 (Layout & Structure)
应用采用 单屏居中卡片式 布局，并严格遵循深色模式的美学设计。
外层容器：
布局：min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-8
背景色：极暗石板色 bg-slate-950 text-slate-200
交互：全局选中文本颜色定制 selection:bg-emerald-500/30
主卡片 (Main Card)：
尺寸与外观：w-full max-w-[560px] bg-slate-900 rounded-2xl shadow-2xl shadow-black/50 border border-slate-800/80
内部结构：垂直 Flex 布局 flex flex-col，分为四个主要区域：
Header (连接配置)：border-b 分割。
Global Settings (脉冲宽度)：位于列表上方。
GPIO List (主控列表)：中间区域，开启纵向滚动 flex-1 overflow-y-auto。
Footer (电平读取)：border-t 分割。
二、 核心数据结构与交互逻辑 (State & Logic)
使用 React State 管理所有交互，最核心的是 GPIO 状态数组。
code
TypeScript
// 1. GPIO 状态定义
type GpioState = 'high' | 'low' | 'high-z';

interface GpioConfig {
  id: string;
  name: string;
  state: GpioState;
}

// 2. 初始化 8 个 GPIO 通道
const INITIAL_GPIOS: GpioConfig[] = [
  { id: 'gpio0', name: 'GPIO0', state: 'high-z' },
  // ... gpio1, gpio6, gpio7, gpio2, gpio8, gpio14, gpio20
];

// 3. React States
const [gpios, setGpios] = useState<GpioConfig[]>(INITIAL_GPIOS);
const [isConnected, setIsConnected] = useState(false);
const [pulseMs, setPulseMs] = useState('100.0');
const [readLevel, setReadLevel] = useState<string | null>(null);

// 4. Toggle 联动逻辑：点击 Toggle 按钮，翻转对应 GPIO 的状态
const handleToggle = (id: string) => {
  setGpios(gpios.map(g => {
    if (g.id === id) {
      // 如果当前是 high 则切换为 low，否则（low 或 high-z）统一切换为 high
      return { ...g, state: g.state === 'high' ? 'low' : 'high' };
    }
    return g;
  }));
};

// 5. 直接点击电平图标修改状态
const handleGpioStateChange = (id: string, newState: GpioState) => {
  setGpios(gpios.map(g => g.id === id ? { ...g, state: newState } : g));
};
三、 区域样式拆解与 SVG 元素 (Styling & SVGs)
除了使用 lucide-react 的通用图标外，我们专门绘制了高电平和低电平的 SVG，纠正了原图中错误的上升/下降沿表示。
1. 自定义电平 SVG 图标
code
Tsx
// 高电平：先垂直向上，再水平向右 (代表稳定的高电平状态)
const HighLevelIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4 16V8h16" />
  </svg>
);

// 低电平：先垂直向下，再水平向右 (代表稳定的低电平状态)
const LowLevelIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4 8v8h16" />
  </svg>
);
2. Header 区 (MCU & 串口配置)
下拉框 (Select)：使用 appearance-none 隐藏原生箭头，自定义外层包裹器实现暗黑风格。获得焦点时有翠绿色的光晕反馈 focus-within:ring-1 focus-within:ring-emerald-500/20。
Connect 按钮状态切换：
未连接：实心翠绿色块 bg-emerald-600 text-white，带发光阴影。
已连接：幽灵按钮样式 bg-emerald-500/10 text-emerald-400，图标产生 rotate-45 的动画过渡。
3. Pulse 宽度全局设置区
从底部移至 GPIO 列表上方，使其在逻辑上更符合“先设置脉宽，再点击具体通道的 Pulse 按钮”的操作流。
输入框：带有 ms 单位的相对定位。字体使用等宽字体 font-mono 以对齐小数点。
4. GPIO 列表单行设计 (最核心部分)
每一行是一个水平 Flex 容器，悬浮时背景提亮 (hover:bg-slate-800/30)。
分段控制器 (Segmented Control)：
外部包裹：p-[3px] bg-slate-950 rounded-lg shadow-inner
内部按钮激活状态：
高电平激活：bg-slate-700 text-emerald-400 (翠绿色)
低电平激活：bg-slate-700 text-rose-400 (玫瑰红)
高阻态/禁用激活：bg-slate-700 text-slate-200
未激活时：淡灰色 text-slate-500，Hover 时微亮。
操作按钮组合：
Pulse 按钮：标准次级按钮 bg-slate-800 text-slate-200。
Toggle 按钮：为了与 Pulse 区分开，使用了靛蓝色的主题 bg-indigo-500/10 text-indigo-400 border-indigo-500/20。
联动体现：点击 Toggle 按钮会触发上面定义好的 handleToggle，React 状态更新后，前面的分段控制器会瞬间自动切换高亮（翠绿/玫瑰红），给用户强烈的视觉联动反馈。
5. Footer 区 (读取区域)
左侧为 GPIO 通道选择下拉框和 Read 按钮（带有 Activity 图标）。
右侧为读取结果回显模块：
结果为 High：文本渲染为翠绿色 text-emerald-400。
结果为 Low：文本渲染为玫瑰红 text-rose-400。
默认：显示为破折号 —，颜色为 text-slate-500。
总结
你只需要准备好 lucide-react (用于 Search, Link, X, Activity, ChevronDown 这几个基础图标) 以及 tailwindcss，然后对照上述的 DOM 结构嵌套（主要是深色 bg 色阶和 emerald/rose/indigo 点缀色），配合 React 的 State 映射逻辑，即可完美还原这个既现代化又专业的硬件控制面板。