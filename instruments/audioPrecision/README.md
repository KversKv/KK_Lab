# APx500 Python 仪器驱动 (分享包)

Audio Precision APx500 .NET API 的 Python 封装驱动,提取自
《Audio Precision 音频自动化测试工具》(ap_noise_test.py)的驱动层
`class APxConnection`,**逻辑与原工具完全一致**,仅去除 GUI 依赖,
可在任何 Python 脚本中独立使用。

- 提取日期: 2026-11-05
- 源文件: ap_noise_test.py 第 457-2264 行 (原文件 MD5: E205CC784B232E2B0CB253197ED8A764)
- 已在实机 APx500 9.3 上验证: 连接、枚举、运行 Level and Gain 测量、读取 8 通道结果

---

## 1. 文件清单

| 文件 | 说明 |
|---|---|
| `apx500_driver.py` | 驱动模块 (唯一必需文件) |
| `apx500_demo.py` | 演示脚本, 含连接/枚举/测量/读数/频谱导出示例 |
| `requirements.txt` | 依赖清单 |
| `README.md` | 本文件 |

## 2. 环境要求

1. **操作系统**: Windows 64 位
2. **Audio Precision APx500 软件**: 9.x (默认路径 `C:\Program Files\Audio Precision\APx500 9.3\API`,
   其他版本见"自定义 API 路径")
3. **Python**: 3.8 及以上 (验证环境: Python 3.13.15)
4. **依赖**: 仅 `pythonnet` (验证版本 3.1.0); 驱动本身只依赖标准库
5. **.NET Framework**: 4.6.1+ (APx500 自带)
6. 运行时: APx500 软件可正常启动, AP 仪器已连接开机
   (Win7 老环境请用 Python 3.8.10 + pythonnet 2.5.2)

## 3. 安装与快速验证

```bat
pip install -r requirements.txt

:: 1) 环境自检: 连接并列出 Signal Path / 测量项
python apx500_driver.py

:: 2) 演示: 枚举所有测量与结果图
python apx500_demo.py --list-only

:: 3) 演示: 真实测量 (Level and Gain, 读取 RMS Level)
python apx500_demo.py

:: 4) 演示: 底噪测量, 带标准滤波 (20Hz-20kHz 椭圆 + SignalPath 加权)
python apx500_demo.py --meas "Noise (RMS)" --attr Level --filters

:: 5) 演示: THD+N, 打开发生器 0.8 Vrms
python apx500_demo.py --meas "THD+N" --attr ThdNRatio --gen 0.8

:: 6) 演示: 频谱测量并导出图片
python apx500_demo.py --spectrum spectrum.png
```

## 4. 快速上手 (代码)

```python
from apx500_driver import APxConnection

ap = APxConnection()
ap.connect()                                   # 连接 APx500 (会显示 APx500 界面)
print(ap.get_signal_path_names())              # ['Signal Path1', ...]

sp = ap.get_signal_path_names()[0]
ap.run_measurement(sp, "Level and Gain")       # 运行单个测量并等待完成

# 读取结果 -> (数值列表, AP显示文本列表, 结果名, 通道数)
values, texts, name, ch = ap.read_by_attr(
    sp, "Level and Gain", "Level", prefer_sequence=True)
print(values, texts)                           # [0.2877...], ['287.8 mVrms', ...]

ap.disconnect()
```

自定义 APx500 安装路径 (其他版本/盘符):

```python
import apx500_driver
apx500_driver.load_ap_api(r"C:\Program Files\Audio Precision\APx500 9.1\API")
```

## 5. API 参考 (APxConnection)

### 连接管理
| 方法 | 说明 |
|---|---|
| `connect()` | 创建 APx500 实例并显示其界面 |
| `disconnect()` | 断开连接 (隐藏界面) |
| `connected` (property) | 连接是否有效 (坏连接自动置 False) |
| `log_callback` | 可赋值回调函数 `f(str)`, 接收驱动内部诊断日志 |

### 枚举与定位
| 方法 | 说明 |
|---|---|
| `get_signal_path_names()` | 全部 Signal Path 名称 |
| `get_active_signal_path()` | 当前激活的 Signal Path |
| `get_measurement_names(sp)` | 该 Signal Path 下全部测量名 |
| `get_result_graph_names(sp, meas)` | 该测量的全部结果图名 |
| `get_all_measurement_types()` | AP 支持的全部测量类型 |
| `resolve_measurement_name(sp, name)` | 按名称模糊匹配测量, 找不到可自动添加 |
| `show_measurement(sp, meas)` | 在 AP 界面切到该测量 |
| `MEASUREMENT_PROPS` | 测量名 -> AP 属性名映射 (如 "THD+N" -> "ThdN") |

### 运行与读数
| 方法 | 说明 |
|---|---|
| `run_measurement(sp, meas)` | 运行单个测量并等待完成 (超时 15s) |
| `run_sequence()` | 运行整条 Sequence |
| `read_by_attr(sp, meas, attr, prefer_active_meter=False, prefer_sequence=False)` | **核心读数接口**, 返回 `(values, texts, name, ch_count)` |
| `read_measurement_result(sp, meas, result_name=None)` | 按结果名/任意可用 meter 读数 |

**read_by_attr 取值策略** (驱动内置 meter 与序列结果双通道):

- 默认: 优先有效 meter 值, 无效则回退序列结果, 均无效重试 3 次
- `prefer_active_meter=True`: 强制取当前界面 meter (THD+N 用, 与 AP 界面显示对齐)
- `prefer_sequence=True`: 强制取序列运行期间的结果
  (输出幅度测量必须用: 序列跑完发生器会关闭, 此时 meter 读到的只是底噪瞬时值)

常用测量对应的 attr 名 (与 GUI 工具一致):

| 测量 | attr | prefer 策略 |
|---|---|---|
| Noise (RMS) | `Level` | 默认 |
| THD+N | `ThdNRatio` | `prefer_active_meter=True` |
| Level and Gain | `Level` | `prefer_sequence=True` |

**THD+N 单位换算** (GUI 工具同款规则):
- AP 显示文本含 `%` (如 "0.0312 %")时: `dB = 20*log10(|数值|/100)`
- 数值 <= -1.0: 视为已是 dB
- 数值 > 0: 视为比值, `dB = 20*log10(数值)`

### 发生器控制
| 方法 | 说明 |
|---|---|
| `set_generator_on(level_vrms=0.8)` | 开发生器并设双通道电平 (BenchMode/各测量/SignalPathSetup 多层写入) |
| `set_generator_off()` | 关发生器 (含各层) |
| `set_measurement_generator(ap_prop, on, level)` | 单个测量的发生器 |
| `set_active_generator(on, level_vrms)` | 当前激活测量的发生器 |

### 滤波器配置
| 方法 | 说明 |
|---|---|
| `apply_analyzer_filters(meas_prop, filters)` | 批量配置高通/低通/加权 (写入多层目标对象, 与 AP 界面一致) |
| `set_noise_weighting(weighting, ...)` | 单独设置加权 (`AWeighting`/`SignalPath`/`None`) |
| `set_bandwidth_22k(meas_prop)` | 22.4kHz 低通带宽 |

filters 参数格式 (与 GUI 工具一致):

```python
filters = {
    "highpass": {"enabled": True, "type": "Elliptic", "freq_hz": 20.0},
    "lowpass":  {"enabled": True, "type": "Elliptic", "freq_hz": 20000.0},
    "weighting": "SignalPath",     # 或 "AWeighting" / "None"
}
ap.apply_analyzer_filters("LevelAndGain", filters)   # meas_prop 见 MEASUREMENT_PROPS
```

### 频谱与时域采集
| 方法 | 说明 |
|---|---|
| `run_and_export_spectrum(sp, meas, png_path)` | 运行频谱测量并导出图片 (自动设 dBV) |
| `get_signal_analyzer_fft_data(sp, meas, channel, acq)` | 采集 FFT 频谱 XY 数据 (自动选择最佳频谱图) |
| `get_signal_acquisition_data(sp, meas, channel, acq, acq_time)` | 采集时域波形 |
| `configure_fft_settings(sp, meas)` | FFT 参数 (48000 点/Equiripple/7 次平均) |

## 6. 常见问题

- **"无法加载 AudioPrecision.API.dll"**: APx500 未安装, 或用 `load_ap_api("实际路径")` 指定;
  也确认已 `pip install pythonnet`
- **连接失败**: 确认 APx500 软件能正常打开、仪器已连接并开机
- **测量名不匹配**: Signal Path/测量名以 AP 工程文件为准 (本机为 `Signal Path1`);
  `resolve_measurement_name` 支持模糊匹配与自动添加
- **读数为空/N/A**: 先 `run_measurement` 再读; "尚未执行" 表示该测量无序列结果
- **与完整 GUI 工具的关系**: 本驱动即 GUI 工具的驱动层, 逐行提取无改动;
  完整工具 (I2C/流程编排/报告导出) 另行分享

## 7. 验证记录 (2026-11-05, APx500 9.3 实机)

```
连接 APx500 ... Signal Paths: ['Signal Path1']
Measurements: ['Level and Gain', 'THD+N', 'Frequency Response', ...]
运行测量: Level and Gain
结果: RMS Level (8 通道)
数值: [0.2877, 0.2946, ...]  文本: ['287.8 mVrms', '294.7 mVrms', ...]
已断开 APx500
```
