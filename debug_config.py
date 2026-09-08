DEBUG_MOCK = False

# Module Test 逐节点 DEBUG（截图 + 事件日志，Load Transient / Ripple 等 scope 项）：
# 开启后在报告目录 debug/ 下按流程节点落盘示波器屏幕截图（定位波形异常），
# 并把详细事件（含绝对时间戳与相对耗时）追加写入 debug/events.log，
# 与截图节点对照定位问题步骤；改值后须重启应用（同 DEBUG_MOCK）
MODULE_TEST_DEBUG = False

# Module Test 报告「各测试项耗时汇总」开关（开发者 DEBUG / 性能调试用）：
# 开启后 runner 逐项记录耗时，报告 Meta 区追加各测试项耗时表（含占比）；
# 关闭时数据不出现在 REPORT_DATA（正式报告无耗时表）；改值后须重启应用（同 DEBUG_MOCK）
REPORT_ITEM_TIMING = True
