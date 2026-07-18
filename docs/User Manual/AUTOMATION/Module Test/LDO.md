# LDO Module Test

LDO 模块测试页，绑定 `LDO_ITEMS` 注册表，对芯片内各 LDO 执行输出电压精度、负载调整率、PSRR、瞬态响应等测试项。

## 页面入口

- 导航栏 → `AUTOMATION` → `Module Test` → 子菜单 `LDO`
- 对应源码：`ui/pages/module_test/ldo_test_ui.py`（`LDOTestUI`）
- Page Key：`module_test_ldo`

## 界面布局

继承自 `ModuleTestSubPageBase` 通用框架：

### 1. 顶部仪器连接区
- **N6705C 连接卡片**：`N6705CConnectionMixin`，提供 Vin / Vout 测量。
- **Oscilloscope 连接卡片**：`OscilloscopeConnectionMixin`，捕获纹波与瞬态。
- **Chamber 连接卡片**：`ChamberConnectionMixin`，温漂测试。

### 2. 左侧 — 测试项配置区
- **Test Items Table**：列出 `LDO_ITEMS` 中所有测试项，每行：勾选框 / 名称 / 模块 / 配置按钮 / 状态。
- 表格高度按 `header + 30px × 行数` 计算，垂直 Expanding 防截断。
- 点击配置按钮弹窗编辑该测试项的参数。

### 3. 右侧 — 结果展示区
- **结果摘要表**：模块 / 测试项 / 实测值 / 期望值 / 误差 / PASS-FAIL。
- **图表区**：根据所选测试项动态切换（电压曲线、纹波波形、PSRR 频谱等）。

### 4. 底部 — Execution Logs
- 打印每个测试项的执行步骤、I2C 写入、N6705C/示波器回读、PASS-FAIL 判定。

## 典型操作流程

1. 在 N6705C Analyser 与 Oscilloscope 页连接好仪器。
2. 进入本页 → 在 Test Items Table 勾选要执行的测试项（如 LDO_01 输出电压、LDO_01 负载调整率）。
3. 点击每行的配置按钮 → 弹窗设电压范围、负载电流范围、采样次数等。
4. 点击 `▷ Start Sequence`。
5. `LDOTestRunner` 按勾选顺序逐项执行，结果实时写入摘要表与日志。
6. 测试完成保存 HTML 报告 + CSV。

## 关键参数说明

| 参数 | 单位 | 说明 |
|---|---|---|
| Vin | V | LDO 输入电压 |
| Vout | V | LDO 输出电压 |
| Load Current | mA | 负载电流（测试负载调整率时扫描） |
| PSRR Frequency | Hz | PSRR 测试的注入纹波频率 |
| Settling Time | ms | 设置后等待稳定时间 |

## 注意事项

- **Runner 解耦**：`LDOTestRunner` 是纯函数实现，可独立运行（`python -m core.module_test.ldo.ldo_runner`），便于 CI 集成。
- **测试项扩展**：新增测试项在 `core/module_test/ldo/items.py` 的 `LDO_ITEMS` 注册，自动出现在表格。
- **AI 契约**：实现 5 个能力，AI 可批量执行测试项。
- **Mock 模式**：`DEBUG_MOCK=True` 时全部走 Mock。
- **结果文件**：输出到 `Results/module_test_ldo/<时间戳>/`，含 HTML 报告（含 PASS/FAIL 表 + 内嵌波形图）+ CSV。
- **不要复用 PMU Worker**：本页 Runner 独立实现，禁止再引入 PMU 的 QThread Worker 造成 Qt 耦合。
