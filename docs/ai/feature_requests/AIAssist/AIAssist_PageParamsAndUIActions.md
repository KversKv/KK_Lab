# AI Assistant 各页面「常用参数 + UI 动作」汇总（受控能力清单）

> 范围：在 [AIAssist_PageScopedControlPlan.md](./AIAssist_PageScopedControlPlan.md) 的「页面契约（§2）+ 枢纽去硬编码（§3）+ UI 回填（§4）+ 按页裁剪（§5）+ `ui_invoke` 注册表（§5b）」基础上，**逐页落地登记**各页面：
> - **常用配置参数**（AI 经 `apply_test_config_draft` → `ai_apply_config` → `apply_config_to_controls` 可写的键，键名以页面 `get_test_config()` 输出为准）；
> - **常用 UI 动作**（页面上有按钮但无专用接口者，经 `register_ui_action(...)` 登记，AI 经 `list_ui_actions` / `ui_invoke` 触发）。
>
> 本文档既是「实现该登记工作」的施工清单，也是给各页 Profile `system_prompt` 声明参数词表的事实源，避免模型臆造键名 / 误判可否修改。

---

## 0. 现状结论（先行）

| 层 | 状态 | 说明 |
|---|---|---|
| 页面契约 `AIControllablePage` | ✅ 已实现 | [page_contract.py](../../../core/ai/page_contract.py)，10 个页面实现 `ai_capabilities`（5 PMU 子页 + 4 charger 子页 + orchestrator） |
| 枢纽去硬编码 + 子页下钻 | ✅ 已实现 | [`resolve_active_ai_page()`](../../../ui/main_window.py#L1285) |
| 配置写链路 | ✅ 已通 | `_apply_ai_config_draft` → 子页 `ai_apply_config` → `apply_config_to_controls` |
| 按页裁剪 tools | ✅ 已实现 | `to_tools(capabilities)` + `ACTION_CAPABILITY_MAP` |
| `ui_invoke` 注册表 | ⚠️ **框架在、无数据** | [ui_action_registry.py](../../../core/ai/ui_action_registry.py) 已建，`list_ui_actions`/`ui_invoke` 已注册，但**全工程 `register_ui_action` 零调用** → AI 无任何 UI 按钮可触发 |

**故障对位**：用户在 `pmu_dcdc_efficiency` 让 AI 改参数，AI 回「无法直接修改配置参数」。该页 `ai_apply_config` / `apply_config_to_controls` 实际已实现，写链路通。本汇总用于：
1. 给各页 Profile 写入**明确的可写参数词表**（消除模型「我没有修改接口」的误判）；
2. 补齐 §5b 的真正缺口——**逐页 `register_ui_action`** 把 Auto Set / Zero / 导出等按钮纳入 AI 可触发白名单。

> 键名约定：下表「参数键」即 `apply_test_config_draft` 的 `config_draft` 字典键，与页面 `get_test_config()` 输出对齐；电流类支持 `*_a`（安培）与 `*_ma`（毫安别名，由 `apply_config_to_controls` 内部换算，见 dcdc 实现）。

---

## 1. PMU 测试子页（容器 `pmu_test`，按当前 Tab 子页裁剪）

### 1.1 `pmu_dcdc_efficiency` — DCDC 效率测试

能力：`get_config / apply_config / start_test / stop_test / get_result`

**常用参数（`config_draft` 键）**

| 参数键 | 控件 | 含义 / 单位 | 备注 |
|---|---|---|---|
| `test_item` | `test_item_combo` | 测试项 | `Efficiency Curve` / `VIN Sweep` / `Temperature Sweep` |
| `sweep_mode` | Linear/Log 分段 | 扫描方式 | `Linear` / `Log` |
| `start_current_a` | `load_current_start_spin` | 起始电流 (A) | 支持 `start_current_ma` 别名 |
| `end_current_a` | `load_current_end_spin` | 结束电流 (A) | 支持 `end_current_ma` 别名 |
| `step_current_a` | `step_current_spin` | 步进电流 (A) | Linear 模式有效 |
| `points_per_dec` | `points_per_dec_spin` | 每十倍点数 | Log 模式有效 |
| `average_cnt` | `average_cnt_spin` | 每点平均次数 | |
| `settle_time_ms` | `settle_time_spin` | 稳定时间 (ms) | |
| `sampling_method` | `sampling_method_combo` | 采样方式 | `Instant MEAS` / `DataLogger` |
| `dlog_duration_s` | `dlog_duration_spin` | DataLog 时长 (s) | |
| `vin_start/end/step` | `vin_*_spin` | VIN 扫描 (V) | 仅 `VIN Sweep` 暴露 |
| `temp_start/end/step` | `temp_*_spin` | 温度扫描 (℃) | 仅 `Temperature Sweep` 暴露 |
| `fixed_load_a` | `temp_fixed_load_spin` | 固定负载 (A) | 仅 `Temperature Sweep` |
| `vin_channel` / `vout_channel` / `cc_load_channel` | 对应 combo | N6705C 通道 | |

**建议登记的 UI 动作（`register_ui_action`）**

| action_id | label | handler（按钮原槽） | risk | enabled_when |
|---|---|---|---|---|
| `pmu_dcdc_efficiency.export_csv` | 导出结果 CSV | `_on_export_csv` | low | 有结果数据 |
| `pmu_dcdc_efficiency.import_csv` | 导入结果 CSV | `_on_import_csv` | low | 恒可用 |

> 启停已有专用契约（`ai_start_test`/`ai_stop_test`），**不再**登记为 ui_invoke，避免双通道。

### 1.2 `pmu_output_voltage` — 输出电压线性度

**常用参数**

| 参数键 | 含义 / 单位 |
|---|---|
| `output_channel` | 输出通道 |
| `set_voltage` | 设定电压 (V) |
| `load_current_min` / `load_current_max` | 负载电流范围 (A) |
| `current_step` | 电流步进 (A) |
| `measure_count` | 测量次数 |
| `stabilize_time` | 稳定时间 (ms) |
| `sample_interval` | 采样间隔 |
| `enable_ovp` / `ovp_value` | OVP 使能 / 阈值 (V) |
| `vmeter_channel` | 电压表通道 |
| `device_addr` / `reg_addr` / `msb` / `lsb` / `width_flag` | IIC 读取配置 |
| `min_code` / `max_code` | DAC 代码范围 |

**建议登记 UI 动作**：导出 / 导入结果（同 dcdc 模式）。

### 1.3 `pmu_is_gain` — IS Gain 测试

**常用参数**

| 参数键 | 含义 / 单位 |
|---|---|
| `ripple_channel` / `load_channel` | 纹波 / 负载通道 |
| `is_gain_method` | 采集方法 |
| `is_gain_device_addr` / `is_gain_reg_addr` / `is_gain_msb` / `is_gain_lsb` | IIC 寄存器配置 |
| `is_gain_start_current` / `is_gain_end_current` / `is_gain_step_current` | 负载电流扫描 (A) |
| `save_screenshot` | 是否保存示波器截图 |

### 1.4 `pmu_oscp` — OSCP/OVP/UVP/SCP 保护点

**常用参数**

| 参数键 | 含义 / 单位 |
|---|---|
| `test_type` | `OCP`/`SCP`/`OVP`/`UVP` |
| `method` | `Reg` / 监控通道法 |
| `test_channel` | 测试通道 |
| `delay_time_ms` | 延时 (ms) |
| `current_start/end/step` | 电流扫描 (A)，`OCP/SCP` 用 |
| `voltage_start/end/step` | 电压扫描 (V)，`OVP/UVP` 用 |
| `device_address` / `register_address` / `iic_width` | Reg 法 IIC 配置 |
| `monitor_channel` | 监控法通道 |

### 1.5 `pmu_gpadc` — GPADC 测试

**常用参数**

| 参数键 | 含义 / 单位 |
|---|---|
| `test_item` | 测试项（1000CNT / 线性度等） |
| `data_acquisition_mode` | `IIC` / `UART` |
| `iic_device_address` / `iic_data_address` | IIC 地址 |
| `dut_port` / `uart_keyword` | UART 口 / 关键字 |
| `voltage_channel` | 电压通道 |
| `voltage_min/max/step` | 电压扫描 (V) |
| `temp_min/max/step` | 温度扫描 (℃) |
| `soak_time` | 保温时间 (s) |

---

## 2. Charger 测试子页（容器 `charger_test`）

> 4 个子页（`config_traverse` / `status_register` / `iterm` / `regulation_voltage`）均已实现 `ai_capabilities`；参数键以各自 `get_test_config()` 为准，登记规则同 PMU（扫描范围 / 通道 / IIC 寄存器 / 步进），导出类按钮经 `register_ui_action` 纳管。

| 子页 page_key | 重点参数方向 |
|---|---|
| `charger_config_traverse` | 配置遍历范围、寄存器组合 |
| `charger_status_register` | 状态寄存器读取地址 |
| `charger_iterm` | 终止电流扫描范围 (A) |
| `charger_regulation_voltage` | 调压点扫描范围 (V) |

> 落地时按 §1 同样形式补全各子页参数表（读各自 `get_test_config()`）。

---

## 3. 仪器主页 / 编排页

### 3.1 `power_analyser`（N6705C 电源分析仪）

无 `ai_capabilities`（非测试序列页），但有典型「无专用接口的页面按钮」，是 `ui_invoke` 的主要受益者。

**建议登记 UI 动作**

| action_id | label | risk | enabled_when |
|---|---|---|---|
| `power_analyser.auto_set` | Auto Set（自动量程/挡位） | medium | 已连接仪器 |
| `power_analyser.zero` | Zero（清零） | medium | 已连接仪器 |
| `power_analyser.calibrate` | Calibrate（校准） | high | 已连接仪器 |

> N6705C 的 Analyser UI 构造已透传 `ui_action_registry`（见 [main_window.py](../../../ui/main_window.py#L1365)），页面侧补 `register_ui_action(...)` 即可。

### 3.2 `datalog`（N6705C DataLog）

**建议登记 UI 动作**：`datalog.auto_fit`（Auto Fit 自适应缩放，low）、导出（low）。

### 3.3 `orchestrator`（测试编排）

能力最全（9 项）：脚本草案落地 / 启停 / 暂停 / 单步 / 列步骤 / 设变量等，已走专用受控动作，**无需 ui_invoke 补充**。

---

## 4. 落地施工清单（最小改动，零改 core / 零改 handler）

每页只需两类动作，均在页面类内、构建控件之后执行：

1. **参数词表**（消除「无法修改」误判）：在对应 Profile `system_prompt` 列出本页可写参数键（取本文档表格），明确「可经 `apply_test_config_draft` 修改这些参数」。文件：[profiles.py](../../../core/ai/profiles.py)。
2. **UI 动作登记**（补 §5b 缺口）：页面构建后调用 `register_ui_action(UIActionSpec(...))`，`handler` 直接指向按钮原 `clicked.connect` 的槽，`page_key` 与 [`_get_current_help_key`](../../../ui/main_window.py#L1595) 返回值对齐，`enabled_when` 给连接/数据前置校验。

```python
# 页面 _bind_signals 末尾或构建完成后（registry 经构造注入）：
if self._ui_action_registry is not None:
    self._ui_action_registry.register(UIActionSpec(
        id="pmu_dcdc_efficiency.export_csv",
        label="导出结果 CSV",
        page_key="pmu_dcdc_efficiency",
        handler=self._on_export_csv,        # 复用按钮原槽，行为与人点一致
        risk="low",
        enabled_when=lambda: bool(self._export_data),
    ))
```

**安全红线（沿用 §5b.5 / §6）**：白名单制；`ui_invoke` 仍过 `PermissionChecker` + 确认 + `AuditLog`；handler 一律主线程 Slot；`enabled_when` 前置校验拒绝盲点；仅触发 `page_key == 当前页` 的动作。

---

## 5. 进度表

> 状态：`☐ 未开始` / `◐ 进行中` / `☑ 已完成`。

| # | 任务 | 文件 | 状态 |
|---|---|---|---|
| 5.1 | 汇总各页参数键 + UI 动作（本文档） | 本文件 | ☑ |
| 5.2 | 各 PMU 子页 Profile 写入可写参数词表 | `core/ai/profiles.py` | ☐ |
| 5.3 | `pmu_dcdc_efficiency` 登记导出/导入/图表自适应 UI 动作 | `ui/pages/pmu_test/pmu_dcdc_efficiency.py` | ☑ |
| 5.4 | 其余 PMU 子页登记（`pmu_is_gain` 导出 / `pmu_gpadc` 导出，含 registry 透传 `pmu_test_ui.py`） | 各页面 | ☑ |
| 5.5 | `power_analyser` 登记 Auto Set / Zero / Calibrate | `ui/pages/n6705c_power_analyzer/*` | ◐ (Auto Set 已登记) |
| 5.6 | `datalog` 登记 Auto Fit / 导出 | `ui/pages/n6705c_power_analyzer/*` | ☐ |
| 5.7 | 端到端：dcdc 改参数 + `ui_invoke` 触发 Auto Set 验证 | — | ☐ |
