# IIC Control

IIC Control 是 **USB-I2C 寄存器读写工具**，支持手动读写单个寄存器、位域合并、寄存器映射模板、序列脚本（DSL）批量执行、芯片识别检查。常用于 PMU 寄存器调试。

## 页面入口

- 导航栏 → `TOOLS` → `Collection` → 子菜单 `IIC Control`
- 对应源码：`ui/modules/IIC_Module/i2c_mixin.py`（`I2cMixin`），由 `main_window.py::_I2cControlPage` 包装。
- 详细使用指引见 `docs/user/IIC_Module/Sequence_Script_Guide.md` 与 `docs/user/IIC_Module/Template_Guide.md`。

## 界面布局

采用 `QTabWidget` 三个标签页，分别对应三种使用场景：

### 1. 控制（Register Access + Bit Field View）
- **Device Address**：I2C 设备地址（如 0x17）。
- **Speed Mode**：100K / 400K / 1M。
- **Reg Address**：寄存器地址（hex，支持 8/16/24/32 位宽度切换）。
- **Data Value**：数据值（hex）。
- **Read / Write 按钮**：触发单次读写（异步 Worker）。
- **Bits Table**：位域视图，按位解析当前数据值，可单独勾选/取消勾选位。
- **Hex / Bin 显示**：当前值的 hex 与分组 bin 显示。

### 2. 模板（Register Map + Save/Load）
- **Template Combo**：从已保存的模板列表中选择（模板文件位于 `_i2c_template_dir()`）。
- **Register Map 表**：列出模板中所有寄存器的名称、地址、位域、默认值、描述。
- **Save / Load / Delete 按钮**：保存当前模板 / 加载模板到表 / 删除模板。
- **New Template**：新建空白模板。
- 模板持久化由 `i2c_persistence.py` 实现，文件格式为 YAML。

### 3. 设置（DLL path + default speed/bit width + Chip Check）
- **DLL Path**：USB-I2C DLL 路径（默认由系统查找）。
- **Default Speed**：默认速率。
- **Default Bit Width**：默认位宽。
- **Chip Check 按钮**：触发 `_I2cChipCheckWorker`，读取芯片 ID 寄存器，验证芯片型号是否匹配。

### 4. 底部 — Execution Logs
- 打印每次读写操作、Chip Check 结果、序列脚本执行进度。
- 异常带 `exc_info=True` 详细堆栈。

## 典型操作流程

### 流程一：手动读写单个寄存器
1. 进入本页 → 设置 DLL Path（首次使用）→ Chip Check 验证芯片连接。
2. 切到控制标签页 → 输入 Device Address（如 0x17）、Reg Address（如 0x1A）。
3. 点击 Read → 数据值区显示读回值（如 0x0034），位域表自动解析。
4. 修改某些位的勾选 → 数据值自动合并 → 点击 Write → 写入寄存器。
5. 再次 Read 验证写入成功。

### 流程二：使用寄存器映射模板
1. 切到模板标签页 → 从 Template Combo 选择已保存的模板（如 `BES1811_PMU`）。
2. Register Map 表列出所有寄存器。
3. 双击表行 → 跳转到控制标签页，自动填充 Reg Address 与位域定义。
4. 读写操作后，可保存当前模板的新默认值。

### 流程三：批量执行序列脚本
1. 在模板标签页下方编辑序列脚本（DSL 语法，详见 `Sequence_Script_Guide.md`）。
2. 脚本示例：
   ```
   write 0x1A 0x0034
   delay 100
   read 0x1B
   write 0x1C 0x00FF
   ```
3. 点击 Run Sequence → `_I2cSequenceWorker` 按行执行，每行结果写入日志。
4. 可保存脚本为 YAML 文件供下次加载。

## 关键参数说明

| 参数 | 说明 |
|---|---|
| Device Address | I2C 设备地址（7 位 + R/W 位自动处理） |
| Speed Mode | 100K / 400K / 1M |
| Reg Address Width | 8 / 16 / 24 / 32 位 |
| Data Value Width | 8 / 16 / 24 / 32 位 |
| Bit Field | 位域名称 + 起止位 + 描述（来自模板） |

## 注意事项

- **I2C 即用即销**：每次操作新建 I2C 接口，结束后立即销毁，不持久化连接状态（与项目约定一致）。
- **位宽自动推断**：`_infer_reg_bits` 根据寄存器地址值大小自动推断所需位宽（如地址 0x1A 用 8 位，0x1234 用 16 位）。
- **位域合并**：Bits Table 中勾选位会自动合并到 Data Value，无需手动算 hex。
- **模板文件位置**：`_i2c_template_dir()` 返回的目录，文件为 YAML 格式。
- **序列脚本 DSL**：支持 `write` / `read` / `delay` / `comment` 等指令，详见 `Sequence_Script_Guide.md`。
- **Chip Check**：依赖芯片定义文件（如 `chips/bes1811_pmu.py` 中的 ID 寄存器地址与期望值），未定义的芯片无法 Check。
- **Mock 模式**：`DEBUG_MOCK=True` 时 I2C 走 MockI2C，读写值为模拟。
- **不要硬编码地址与位宽**：必须从 UI 输入或模板读取。
- **三个标签页统一暗色风格**：使用 `_I2C_DARK_STYLE`，按钮高度 `I2C_BTN_HEIGHT`。
