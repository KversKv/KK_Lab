# 04 - 架构细节与分层职责

## 1. 总体分层

```
main.py
  │
  ├─ ui/               (Qt 界面 / 事件 / 展示)
  │   ├─ main_window.py
  │   ├─ pages/        (功能页面：按仪器/功能分组)
  │   ├─ widgets/      (通用控件：sidebar / 暗色下拉框 / pyqtgraph 图)
  │   ├─ styles/       (QSS 样式 + 连接区域 Mixin)
  │   └─ dialogs/      (预留)
  │
  ├─ core/             (业务编排 / 数据流)
  │   ├─ test_manager.py
  │   ├─ data_collector.py
  │   └─ controllers/  (如 oscilloscope_controller)
  │
  ├─ instruments/      (纯仪器驱动，无 UI 依赖)
  │   ├─ base/         (InstrumentBase / VisaInstrument / Exceptions)
  │   ├─ scopes/       (keysight/dsox4034a, tektronix/mso64b)
  │   ├─ power/        (keysight/n6705c + datalog 处理)
  │   ├─ chambers/     (vt6002_chamber)
  │   ├─ adapters/     (预留：通信适配器)
  │   ├─ mock/         (Mock 实现，DEBUG_MOCK=True 时启用)
  │   └─ factory.py    (唯一创建入口)
  │
  ├─ lib/              (底层 / 第三方封装)
  │   ├─ i2c/          (CH341 / BES USB-IO I2C 封装)
  │   └─ download_tools/ (dldtool.exe 包装)
  │
  ├─ chips/            (芯片配置数据：YAML + Python 类)
  ├─ resources/        (icons / QSS / 图像)
  ├─ helps/            (HTML 帮助文档)
  ├─ hooks/            (PyInstaller hooks)
  └─ spec/             (PyInstaller spec)
```

## 2. 层间依赖规则（铁律）

| 上层 | 允许依赖 | 禁止依赖 |
|---|---|---|
| `ui/` | `core/`, `instruments/factory`, `resources/` | 直接 VISA/串口/I2C 阻塞调用 |
| `core/` | `instruments/`, `lib/`, `log_config`, `debug_config` | Qt Widget、`PySide6.QtWidgets` |
| `instruments/` | `lib/`, `log_config`, `debug_config` | 任何 UI / Qt Widget |
| `lib/` | 第三方 / 标准库 | 业务代码、Qt、`instruments` |

## 3. 模块职责

### 3.1 入口 `main.py`
- 容错补齐 `sys.stdout/stderr`、启用 `faulthandler`。
- `setup_logging`、加载图标、`QApplication` 初始化。
- 安装 `HoverFixStyle` 与 Qt `messageHandler`。
- 启动 `MainWindow`。

### 3.2 `ui/main_window.py`
- 侧边栏导航 + `QStackedWidget` 切页。
- 各仪器连接状态管理（N6705C A/B 双台 / 示波器自动识别 / 温箱）。
- 作为 Signal/Slot 的顶层宿主，把仪器连接共享给各页面。

### 3.3 `ui/pages/`
- 按仪器 / 功能分包：`n6705c_power_analyzer/`、`oscilloscope/`、`pmu_test/`、`charger_test/`、`chamber/`、`consumption_test/`。
- 每个页面负责：UI 布局 + 用户交互 + 调用 `core/` 执行业务 + 订阅结果信号刷新图表/表格。

### 3.4 `ui/styles/`
- **样式常量**：`SCROLLBAR_STYLE`、`START_BTN_STYLE` 等。
- **连接区域 Mixin**：`n6705c_module_frame.py`、`oscilloscope_module_frame.py`、`chamber_module_frame.py`、`serialCom_module_frame.py`。
  - 统一提供 "VISA/串口搜索 + 连接/断开 + 状态指示" 一套 UI；
  - 页面通过 **多继承** 混入，避免重复布局。
- **执行日志 Mixin**：`execution_logs_module_frame.py` 提供日志显示区 + 进度条。

### 3.5 `ui/widgets/`
- `sidebar_nav_button.py`：带 checked/unchecked 状态的侧边栏按钮。
- `plot_widget.py`：pyqtgraph 曲线图（暗色主题）。
- `dark_combobox.py`：暗色主题下拉框。

### 3.6 `core/`
- `test_manager.py`：测试生命周期编排，跨仪器的"开始/停止/暂停"总线。
- `data_collector.py`：`QTimer` 周期从仪器读取电压/电流数据，发射 `data_updated` 信号供 UI 订阅。
- `controllers/`：细分控制器（如示波器控制器），封装"连接/断开/测量/截图"等粗粒度操作。

### 3.7 `instruments/`
- `base/instrument_base.py` 抽象基类（`connect / disconnect / is_connected / identify`）。
- `base/visa_instrument.py` 通用 VISA 操作，子类复用。
- `base/exceptions.py` 业务异常（`InstrumentConnectionError` 等）。
- 每类仪器 → 独立子包（`scopes/`、`power/`、`chambers/`）。
- **`factory.py`** 是业务代码获取仪器实例的**唯一入口**；内部可根据 `DEBUG_MOCK` 返回 `Mock*`。
- `mock/mock_instruments.py` 集中维护 `MockN6705C / MockDSOX / MockMSO64B / MockVT6002 / MockI2C`。

### 3.8 `lib/`
- `i2c/`：
  - `Bes_I2CIO_Interface.py` + `i2c_interface_x64.py`：加载 `BES_USBIO_I2C_X64.dll` / `CH341DLLA64.dll`。
  - 高层 API 支持 8/10/32 位地址与数据宽度。
  - `efuse_script_caller.py` 动态加载 `config/EFUSE_SCRIPTS/*.py` 执行 eFuse 烧录。
- `download_tools/`：封装 `dldtool.exe`（Flash / RamRun / 擦除 / eFuse）。

### 3.9 `chips/`
- `bes_chip_configs/main_chip_configs/*.yaml`：芯片参数表（电压 / 电流 / PMU / Charger 默认配置）。
- `bes_chip_configs/main_chips/*.py`：对应的 Python 配置类，提供类型安全的访问接口。
- `pmu_chips/`：单独 PMU 芯片（如 1806p / 1810 / 1813）配置。

## 4. 数据流示例：PMU 输出电压测试

```
用户在 pmu_output_voltage.py 点击 [开始]
  │
  ▼
 page.slot_start() ──emit start_signal──▶ core.test_manager.PmuOutputVoltageTest
                                           │
                                           ├─ DataCollector (QTimer, 子线程)
                                           │      │
                                           │      ├─ instruments.factory.create_power_analyzer()
                                           │      └─ N6705C.measure_current_voltage()
                                           │
                                           └─ 结果 emit data_updated ──▶ UI plot_widget 刷新
```

关键点：
1. UI **不直接**调 `N6705C`；走 `core` → `factory`。
2. `DataCollector` 生活在 QThread，读取阻塞不影响 UI。
3. 跨线程返回数据全部用 Signal/Slot。

## 5. 打包架构

- `spec/kk_lab.spec` 声明 `datas / binaries / hiddenimports / hookspath`。
- `hooks/hook-pyqtgraph.py` 收集 pyqtgraph 资源。
- 资源定位统一用 `sys._MEIPASS`（见 [main.py:L84-L89](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L84-L89)）。

## 6. 扩展点

| 扩展场景 | 看这里 |
|---|---|
| 新增仪器 | [05_INSTRUMENT_GUIDE.md](./05_INSTRUMENT_GUIDE.md) |
| 新增页面 | [06_PAGE_GUIDE.md](./06_PAGE_GUIDE.md) |
| 新增测试 | [07_TEST_GUIDE.md](./07_TEST_GUIDE.md) |
| 架构级决策 | [decisions/](./decisions/) |
