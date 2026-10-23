"""Module Test 报告构建（工程级单文件 HTML · 数据/视图解耦版）。

规划 §7.2 重构：Python 侧把 ``ModuleTestResult`` 序列化为 ``REPORT_DATA`` JSON
注入静态模板，页面全部内容由原生 JS 依 JSON 渲染（无 CDN / 无外链，离线双击可用）。
UI 只拿路径打开，不做 IO——本模块纯字符串生成，禁依赖 Qt。

============================= 数据 Schema（REPORT_DATA） =============================
{
  "meta":    {report_title, module_type, chip, module_name, test_condition,
              operator, temperature_c,
              start_time, end_time, duration_s, generated_at(带时区), sw_version,
              instruments[], environment{},
              item_timing[{index,item_key,title,duration_s}]},
              # item_timing 仅 debug_config.REPORT_ITEM_TIMING=True 时注入（性能调试）；
              # 其余缺字段一律 None → UI 显示 "—"
  "summary": {verdict: PASS|FAIL|N/A, pass, fail, warn, na, total},
  "items": [{
    index, item_key, title, verdict, unit, note,
    metrics: [{key,label,value,unit,precision}],
    charts:  [{id,kind:xy,title,x{key,label,unit,log},series[{key,name,
              type:line|smooth|scatter|bar,axis:left|right}],mark_extrema,
              anomaly{key,op,value}}],
    table:   {file,rows,columns:[{key,label,unit,align,precision,kind:image?,
              fmt:vbit?}],   # kind:image 列单元格 = attachments 下标（截图入表末列）；
              data[[...]],   # fmt:vbit 列单元格仍为十进制 int，前端按 Vbit 进制切换显示
              rules:[{column,op:gt|lt|abs_gt|eq|outlier|mean_pct|dev_gt,value,k,ref,level:warn|fail,hint}
                     | {type:constant,level,hint}]},
    attachments: [{type:image,label,full(dataURI)}]
  }]
}
后端生成约定：仅 ``build_module_html_report(result)`` / ``save_html_report(...)`` 对外；
JSON 经 ``json.dumps`` 并把 ``</`` 转义为 ``<\\/`` 防 script 逃逸。

============================= 设计令牌（CSS Custom Properties） =============================
--bg-base/--bg-raised/--bg-sunk 三层底色；--ink-1/2/3 三级文字；--accent #2F6FED；
语义色 --pass #12A150 / --fail #E5484D / --warn #F5A524 / --na #8B949E（各配 12% 底）；
图表色序 --c1..--c8（色盲安全，语义同时用图标/形状承载）；
--font-ui 系统栈 / --font-mono ui-monospace；数值一律 tabular-nums；
8px 栅格 --sp-1..8；圆角 --r-sm 8 / --r-md 12；阴影仅 --shadow-1/--shadow-2 两级；
正文 14px / 表格 13px / 行高 1.55；:root[data-theme] 深浅双主题。

============================= CHANGELOG（相对旧版关键改进） =============================
 1. 去除 CDN ECharts 依赖 → 纯 SVG 自绘图表引擎，单文件离线可用；
 2. 数据/视图彻底解耦：REPORT_DATA JSON 驱动全页渲染，后端只产 JSON；
 3. 新增 KPI 概览带（总项/PASS/FAIL/N-A/时长/异常点）+ 结论分布 stacked bar；
 4. 新增结论汇总矩阵：结论筛选 chips、行锚点跳转、异常点计数联动；
 5. 关键测量值升级为 MetricCard 网格（值+单位+规格+余量条+状态描边）；
 6. 表格规则引擎：效率>100% 红标、fsw 突变、Diff 跳变(5×MAD)、恒值列告警；
 7. 高级数据表：sticky 表头+首列冻结、排序、列筛选、密度切换、分页、
    >500 行虚拟滚动、当前视图导出 CSV、异常行筛选；
 8. 图表能力：框选缩放/重置、log 轴切换、规格带、参考线、Min/Max 标注、
    Catmull-Rom 平滑折线、十字准线 tooltip、图例点选、导出 PNG；
 9. 深浅双主题（跟随系统 + localStorage 记忆）、中/英一键切换；
10. 左侧固定目录 scroll-spy + 阅读进度条，移动端折叠；
11. 示波器截图缩略图网格 + 灯箱（←/→/Esc、滚轮缩放、测量条件 caption）；
12. 专门 @media print：A4/15mm、强制浅色、自动展开折叠区、表头跨页重复、
    大表截断提示、页眉页脚(机密标识)、签核区；
13. 键盘操作（/ j k e ?）、focus-visible 环、aria 语义、图表表格化替代数据；
14. 缺失字段全局优雅降级为 "—"，数值等宽对齐、单位独立小字、有效位统一；
15. 版式修订（2026-08）：Load/Line Regulation 散点+拟合线 → Catmull-Rom 平滑折线；
    Load Capability&Ripple 示波器截图并入完整数据表末列（附件下标，不重复内嵌）；
    Load/Line Transient 移除分组对比柱状图（数据表与截图网格保留）；
16. 版式修订（2026-08-04）：Output Voltage Scan 首列 DAC_code → Vbit 显示（列
    fmt:vbit，数据仍为十进制 int），表格工具条 BIN/HEX/DEC chips 全局切换进制
    （localStorage 记忆，联动表格/图表刻度/tooltip/图表数据）；Efficiency 移除
    100% 参考虚线（ref_y 已删），图表值域/刻度自适应（log 模式按对数空间留白，
    logTicks 窄域细分 1/2/5×10^e，手动切换 LOG X/Y 后自动贴合数据）；
17. 版式修订（2026-08-04 b）：Vbit 进制切换改到列标题下拉（BIN/HEX/DEC）；行首
    异常图标改固定槽位（未异常行补占位，不再顶错位宽对齐）；Vbit 与数值列统一
    右对齐；Vout Scan 异常 diff 柱标红（bar_anomaly，mean_pct 与表格规则一致）；
    右 Y 轴标题与图区留 26px 边距（左轴 16px）；移除无用的规格带
    （spec_band/spec.spec_band 渲染与 chart_band 切换按钮一并删除）。
18. 判定修订（2026-09-08）：Vout Scan 异常判定基线由全段 Diff 均值（mean_pct）
    改为后端给定的有效段平均步进（新增 dev_gt 规则，容差 = 5% 平均步进）
    ——死区/饱和平台会拉偏全段均值，曾致整列正常步进全部误报；Avg Step
    指标标签注明计算范围（有效段 Vbit 区间）。
19. PDF 输出（2026-09-08）：debug_config.REPORT_PDF_EXPORT 开启时
    save_html_report 经系统 Edge/Chrome 无头打印（pdf_export.py）追加
    report.pdf，并返回 (html_path, pdf_path)；表格 printAll 全量重建
    （取消 >200 行截断至 100 行，详细原始数据全量进 PDF），打印版截图
    网格单列原比例全宽、表内截图 96px→320px。无头打印不依赖 beforeprint
    （headless 下触发不可靠）：由 _to_print_variant 派生打印变体
    （@media print→all 版式前置、版心锁 180mm、__KK_PRINT__ 令 boot
    同步 preparePrint 全量渲染）。

============================= 已知限制 =============================
- Chrome 打印无法用 CSS 计数器输出"第 X/Y 页"，页脚仅含机密标识与生成时间；
- 图表为 SVG 原生打印（非 Canvas），无需位图转换；量纲开关作用于指标卡/表格，
  图表轴单位保持原始量纲。
"""

from core.module_test.report.api import build_module_html_report, save_html_report
from core.module_test.report.data import (
    _build_metrics,  # 兼容 tests/check_ripple_collapse.py 的私有符号引用
    _build_rules,
    _build_table,
    build_report_data,
)

__all__ = [
    "build_module_html_report",
    "save_html_report",
    "build_report_data",
]
