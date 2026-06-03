# VminHunter 工具架构设计（V2 完整版）

基于参考页面（Consumption Test / Output Voltage Linearity Test）与详细需求，重新设计完整架构。

---

## 一、UI 页面布局设计（参考 Consumption Test）

```mermaid
flowchart TB
    subgraph PAGE["VminHunter 测试页面"]
        direction TB
        subgraph TOP["顶部连接区"]
            CONN["设备连接: N6705C / IIC / UART / 温箱 / IO"]
        end
        subgraph LEFT["Test Config 区域"]
            TC1["Test CNT (测试次数)"]
            TC2["测试方式: 内部电压 / 外供电"]
            TC3["温度控制: 启用/禁用 + 温度点"]
            TC4["监测通道: VcoreM(必选) / VcoreL(可选)"]
            TC5["电压点列表 (测试电压)"]
        end
        subgraph MID["Channel Config 区域"]
            CC1["N6705C 通道分配"]
            CC2["VcoreM IIC配置"]
            CC3["VcoreL IIC配置(可选)"]
        end
        subgraph RIGHT["监控与日志区"]
            LOG["UART日志接收 / 实时电压电流 / 死机状态"]
        end
    end
```

### 页面区域明细

| 区域 | 内容                                               |
| ------ | ---------------------------------------------------- |
| **连接区**     | N6705C、IIC、UART、温箱、IO 连接状态与配置         |
| **Test Config**     | Test CNT、测试方式、温控开关、监测通道、电压点列表 |
| **Channel Config**     | N6705C通道、IIC控制字配置（VcoreM/VcoreL）         |
| **监控日志区**     | UART日志、实时监测、死机记录                       |

---

## 二、配置项详细定义

### 1. Test Config 区域

| 配置项 | 类型      | 说明                        |
| -------- | ----------- | ----------------------------- |
| **Test CNT**       | 整数      | 测试次数（替代原Test Time） |
| **测试方式**       | 单选      | `内部电压测试` / `外供电测试`                         |
| **温度控制**       | 开关+列表 | 可选启用；启用时设置温度点  |
| **监测通道**       | 多选      | VcoreM（**必选**）、VcoreL（可选）  |
| **电压点列表**       | 列表      | 待测试的电压值集合          |

### 2. Channel Config 区域（IIC控制字配置）

```mermaid
flowchart TD
    subgraph VM["VcoreM 配置 (必选)"]
        VM0["器件地址 (Device Addr)"]
        VM1["控制位宽 (Bit Width)"]
        VM2["睡眠电压控制地址 + 对应bit"]
        VM3["唤醒电压控制地址 + 对应bit"]
    end
    subgraph VL["VcoreL 配置 (可选)"]
        VL0["器件地址 (Device Addr)"]
        VL1["控制位宽 (Bit Width)"]
        VL2["睡眠电压控制地址 + 对应bit"]
        VL3["唤醒电压控制地址 + 对应bit"]
    end
```

| 通道 | 配置项                                                         |
| ------ | ---------------------------------------------------------------- |
| **VcoreM（必选）**     | 器件地址、控制位宽、睡眠电压控制地址+bit、唤醒电压控制地址+bit |
| **VcoreL（可选）**     | 器件地址、控制位宽、睡眠电压控制地址+bit、唤醒电压控制地址+bit |
| **公共**     | 电压控制字地址                                                 |

---

## 三、整体软件分层架构

```mermaid
flowchart TD
    subgraph UI["UI 层 (参考Consumption Test)"]
        U1["Test Config 面板"]
        U2["Channel Config 面板"]
        U3["监控/日志面板"]
        U4["结果展示 (电压表/死机记录)"]
    end

    subgraph APP["应用层"]
        A1["测试模式调度<br/>内部电压 / 外供电"]
        A2["Vmin遍历引擎<br/>从高到低电压组合"]
        A3["电压校准模块<br/>(内部电压方式)"]
        A4["死机判定与恢复"]
        A5["结果记录与报告"]
    end

    subgraph CORE["核心服务层"]
        B1["测试流程编排器"]
        B2["条件遍历器<br/>(电压点×温度×通道)"]
        B3["LOG解析判定<br/>(死机检测)"]
        B4["恢复管理器<br/>(开机/RESET)"]
        B5["安全保护监控"]
    end

    subgraph HAL["硬件抽象层"]
        C1["VoltageController<br/>(IIC电压控制)"]
        C2["PowerMeasure<br/>(N6705C 源/表双模式)"]
        C3["TempController<br/>(温箱)"]
        C4["PowerSwitch<br/>(IO开机/RESET)"]
        C5["LogReceiver<br/>(UART)"]
    end

    subgraph DRV["驱动层"]
        D1["IIC驱动<br/>(参考Linearity Test)"]
        D2["N6705C驱动 (SCPI)"]
        D3["温箱驱动"]
        D4["IO驱动"]
        D5["UART驱动"]
    end

    UI --> APP
    APP --> CORE
    CORE --> HAL
    C1 --> D1
    C2 --> D2
    C3 --> D3
    C4 --> D4
    C5 --> D5
```

---

## 四、两种测试方式的核心流程

### A. 内部电压测试流程

```mermaid
flowchart TD
    A["开始: 内部电压测试"] --> B["N6705C 设为电压表模式"]
    B --> C["(可选)温箱设温度并稳定"]
    C --> D["电压校准阶段"]
    D --> D1["遍历电压点列表"]
    D1 --> D2["IIC尝试控制字 → N6705C回读Vcore"]
    D2 --> D3["调整控制字逼近目标电压"]
    D3 --> D4["记录每个电压点的最准控制字"]
    D4 --> E["探底测试阶段"]
    E --> E1["从高到低组合电压值"]
    E1 --> E2["IIC写入对应最准控制字(睡眠/唤醒)"]
    E2 --> F["读取UART LOG"]
    F --> G{"芯片死机?"}
    G -->|"否"| H["记录PASS, 下一组合"]
    G -->|"是"| I["记录死机点+条件"]
    I --> J["IO控制: 开机/RESET恢复"]
    J --> K["芯片重启正常?"]
    K -->|"是"| H
    K -->|"否"| L["告警/人工介入"]
    H --> M{"遍历完成?"}
    M -->|"否"| E1
    M -->|"是"| N["生成报告"]
```

### B. 外供电测试流程

```mermaid
flowchart TD
    A["开始: 外供电测试"] --> B["N6705C 设为电压源模式"]
    B --> C["(可选)温箱设温度并稳定"]
    C --> E["探底测试阶段"]
    E --> E1["从高到低组合外供电压值"]
    E1 --> E2["N6705C 设置外供电压输出"]
    E2 --> F["读取UART LOG"]
    F --> G{"芯片死机?"}
    G -->|"否"| H["记录PASS, 下一组合"]
    G -->|"是"| I["记录死机点+条件"]
    I --> J["IO控制: 开机/RESET恢复"]
    J --> K["芯片重启正常?"]
    K -->|"是"| H
    K -->|"否"| L["告警/人工介入"]
    H --> M{"遍历完成?"}
    M -->|"否"| E1
    M -->|"是"| N["生成报告"]
```

> 🔑 **两种方式的核心差异**：
>
> - **内部电压**：N6705C=电压表 + IIC控压 + **需先校准控制字**
> - **外供电**：N6705C=电压源 + 直接设外供电压 + **无需校准**

---

## 五、电压校准模块（内部电压方式核心）

```mermaid
sequenceDiagram
    participant ENG as 校准引擎
    participant IIC as IIC控制器
    participant N67 as N6705C(电压表)

    Note over ENG: 对电压点列表逐个校准
    loop 每个目标电压点
        ENG->>IIC: 写入预估控制字
        IIC-->>ENG: 写入完成
        ENG->>N67: 回读实际Vcore电压
        N67-->>ENG: 实测电压值
        ENG->>ENG: 计算误差, 调整控制字
        Note over ENG: 重复逼近直至最准
        ENG->>ENG: 记录该电压点最优控制字
    end
    Note over ENG: 输出校准表<br/>{电压值: 最准控制字}
```

**校准表结构示例：**

| 目标电压 | VcoreM睡眠控制字 | VcoreM唤醒控制字 | VcoreL睡眠控制字 | VcoreL唤醒控制字 | 实测误差 |
| ---------- | ------------------ | ------------------ | ------------------ | ------------------ | ---------- |
| 0.80V    | 0x3A             | 0x3C             | 0x38             | 0x3A             | ±2mV    |
| 0.75V    | 0x35             | 0x37             | 0x33             | 0x35             | ±3mV    |
| ...      | ...              | ...              | ...              | ...              | ...      |

---

## 六、死机检测与恢复机制

```mermaid
stateDiagram-v2
    [*] --> 正常运行
    正常运行 --> LOG监测: 设置电压
    LOG监测 --> 判定: 解析UART日志
    判定 --> 正常运行: 心跳/关键字正常
    判定 --> 死机状态: 超时/无响应/异常关键字
    死机状态 --> 记录: 记录电压点+条件
    记录 --> IO恢复: 开机/RESET
    IO恢复 --> 重启校验: 等待启动LOG
    重启校验 --> 正常运行: 启动成功
    重启校验 --> 重试: 启动失败
    重试 --> IO恢复: 未超最大次数
    重试 --> 告警: 超最大重试
    告警 --> [*]
```

**死机判定依据（UART LOG）：**

| 判定方式 | 说明                      |
| ---------- | --------------------------- |
| **心跳超时**         | 一定时间内无LOG输出       |
| **异常关键字**         | LOG出现Crash/Hang/Error等 |
| **缺失正常标志**         | 未收到预期的正常运行标志  |

---

## 七、配置文件结构（YAML）

```yaml
test_config:
  test_cnt: 100                    # 测试次数(替代Test Time)
  test_mode: "internal"            # internal(内部电压) / external(外供电)

  temperature:
    enable: true
    points: [-40, 25, 85]

  monitor_channels:
    VcoreM: { enable: true }       # 必选
    VcoreL: { enable: false }      # 可选

  voltage_points: [0.80, 0.75, 0.70, 0.65, 0.60]  # 测试电压列表(从高到低)

channel_config:
  n6705c:
    VcoreM_channel: 1
    VcoreL_channel: 2

  iic:                             # 参考 Output Voltage Linearity Test
    voltage_ctrl_word_addr: 0x10   # 电压控制字地址

    VcoreM:                        # 必选
      device_addr: 0x60
      bit_width: 8
      sleep_voltage:
        ctrl_addr: 0x20
        bit: [7, 0]
      wakeup_voltage:
        ctrl_addr: 0x22
        bit: [7, 0]

    VcoreL:                        # 可选 (enable时生效)
      device_addr: 0x62
      bit_width: 8
      sleep_voltage:
        ctrl_addr: 0x24
        bit: [7, 0]
      wakeup_voltage:
        ctrl_addr: 0x26
        bit: [7, 0]

uart:
  port: "COM3"
  baudrate: 115200
  crash_keywords: ["Hang", "Crash", "Assert"]
  heartbeat_timeout_ms: 2000

recovery:
  io_power_pin: "GPIO_5"
  io_reset_pin: "GPIO_6"
  max_retry: 3
  reset_delay_ms: 100

safety:
  over_current_mA: 2000
  voltage_hard_limit_mV: 400
```

---

## 八、推荐代码目录结构

下面架构基于单一项目为例, 需要根据 实际的项目架构在对应的目录新建对应的子文件夹保存;

```
VminHunter/
├── ui/                          # UI层(参考Consumption Test布局)
│   ├── connection_panel.py      # 设备连接区
│   ├── test_config_panel.py     # Test Config区域
│   ├── channel_config_panel.py  # Channel Config区域
│   └── monitor_log_panel.py     # 监控日志区
├── app/                         # 应用层
│   ├── mode_dispatcher.py       # 内部/外供电模式调度
│   ├── vmin_engine.py           # 电压遍历引擎(从高到低)
│   ├── calibrator.py            # 电压校准(内部电压方式)
│   ├── crash_handler.py         # 死机判定与恢复
│   └── reporter.py              # 结果记录与报告
├── core/                        # 核心服务层
│   ├── sequencer.py             # 流程编排
│   ├── iterator.py              # 条件遍历(电压×温度×通道)
│   ├── log_parser.py            # UART日志解析判定
│   ├── recovery_mgr.py          # 开机/RESET恢复管理
│   └── safety_guard.py          # 安全保护
├── hal/                         # 硬件抽象层
│   ├── voltage_ctrl.py          # IIC电压控制
│   ├── power_measure.py         # N6705C源/表双模式
│   ├── temp_ctrl.py             # 温箱控制
│   ├── power_switch.py          # IO开机/RESET
│   └── log_receiver.py          # UART接收
├── driver/                      # 驱动层
│   ├── iic_driver.py            # 参考Linearity Test
│   ├── n6705c_driver.py
│   ├── chamber_driver.py
│   ├── io_driver.py
│   └── uart_driver.py
├── config/
│   └── *.yaml
└── results/
    ├── calibration/             # 校准表
    └── reports/                 # Shmoo图/死机记录
```

---

## 九、关键设计要点总结

| 要点 | 说明                                                          |
| ------ | --------------------------------------------------------------- |
| 🔄 **N6705C双模式**  | 内部电压方式=电压表；外供电方式=电压源；HAL层封装切换         |
| 🎯 **电压校准**  | 内部电压方式独有，记录每个电压点的最准控制字（睡眠/唤醒分开） |
| 📡 **LOG死机检测**  | UART关键字+心跳超时双重判定                                   |
| 🔌 **IO自动恢复**  | 死机后开机/RESET，让芯片重新工作，无需人工干预                |
| 🧩 **VcoreL可选**  | 配置与遍历逻辑需支持单通道/双通道动态切换                     |
| 📋 **复用参考页面**  | UI布局参考Consumption Test，IIC参考Linearity Test             |

---