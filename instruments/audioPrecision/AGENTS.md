# audioPrecision — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 与 [instruments/AGENTS.md](../AGENTS.md)。本文件仅补充 APx 实机调试的文档加载规则。

## APx525 实机调试必读

- 涉及 APx525 / APx500、Python API、VMware Guest、SSH、共享目录、仪器连接或自动化调试时，开始分析、修改或执行前先阅读 [APx525_VM_AI_Debug_Runbook.md](./APx525_VM_AI_Debug_Runbook.md)。
- 遵循 Runbook 的执行边界：仪器控制程序在 Windows Guest 内运行；主机负责编辑代码并通过 SSH 远程执行，共享目录用于交换代码、日志和结果。
- 排查时先核对 Runbook 中的已确认状态、路径差异和检查步骤，不假设主机能直接控制 APx USB，也不把主机路径当作 Guest 路径。
- 实机运行前确认 USB 直通、APx500 仪器识别、测试项目与授权、信号输出及负载连接；不得覆盖唯一的 APx 测试项目。
- APx500 5.0 PSRR 配置：通道数写 `AnalogInput/AnalogOutput.ChannelCount`，输入 EQ 写 `InputEqChannels[i].Eq="None"`，输出 EQ 写 `OutputEq.Eq="None"`，波形写 `Generator.Waveform="Sine"`；`InputChannelCount`、`InputEq`、`OutputEq`、`Generator.Type/AnalogType` 不可直接赋值。
- `apx_psrr_guest.py` 由 SSH Worker 拼接 `psrr_analysis.py` 与本驱动后执行，依赖拼接后的算法全局函数，禁止当作可独立导入运行的 Guest 脚本。
- PSRR 手动 OUTPUT 与扫频解耦：`configure_psrr_measurement(..., generator_on=None)` 只配置电平并保持当前发生器开关；手动 ON 走持久会话 `output` 命令，扫频不得自动改 ON/OFF，Disconnect 前显式关闭。
- APx500 5.0 手动 OUTPUT 必须激活 Signal Path Setup，`AnalogOutput.ChannelCount` 固定为 1，CH1/CH2 仅通过 `OutputChannelIndex` 选择；依次配置 Analog Unbalanced、Acoustic Off、Output EQ None，再配置 Verify Connections 的 Sine、Test Channel、Level/Offset、100 Hz，最后才写 `SignalPathSetup.Generator.On`；扫频才激活 Signal Analyzer，不得用 `SignalAnalyzer.Generator.On=True` 或重置默认频率。
- Signal Analyzer 必须显式置 `FFTSpectrum.Checked=True`；真机采集调用测量对象 `Start()`，返回后直接读取双通道，`AcquisitionCount=1` 不代表平均未完成，禁等待它达到 `Averages` 或调用不存在的 `Stop()`。
- APx `Start()` / Sequence Batch 会触发模态窗口，SSH 会话 0 即使 `Visible=False` 也会失败；必须在 Guest 交互桌面运行，经 SSH 反向转发维持会话，详见 `03_GOTCHAS §41`。

## VM 交互式 DEBUG 调用链

1. Host 将当前 `psrr_analysis.py + apx500_driver.py + apx_psrr_guest.py` 拼接为脚本，通过 `ssh <profile>` 上传到 Guest `C:\Windows\Temp\KK_Lab\apx_psrr_<token>.py`，确保调试的是 Host 当前代码而非 Guest 旧副本。
2. Host 建立本地 socket listener，并启动 `ssh -N -R 127.0.0.1:<Guest端口>:127.0.0.1:<Host端口> <profile>`；Guest 脚本回连该转发端口，以 socket 替代 stdin/stdout，传输 base64 JSON 的 OUTPUT、sweep、disconnect 命令及测量事件。
3. APx 不再由 SSH stdin 直接启动。Host 通过 SSH PowerShell 创建并启动临时计划任务，执行 `py -3.12 -u <脚本>`；任务 Principal 使用当前 VM 用户、`-LogonType Interactive -RunLevel Highest`，使 Python/APx 进入 VM 当前交互桌面。
4. `APxConnection.connect()` 显式设置 `apx.Visible=True`，随后 `ShowMeasurement(...)`、OUTPUT 和 Signal Analyzer `Start()` 都在该桌面执行，因此能在 VM 看到 AP 页面切换和采集动作。之前直接经 OpenSSH 启动时进程位于隔离的会话 0，即使设置 Visible 也不会显示到用户桌面，且内部 `ShowDialog` 会因 `UserInteractive=False` 失败。
5. DEBUG 结束必须先 OUTPUT OFF，再 disconnect；Host 停止并注销临时计划任务、关闭隧道，删除 Guest 临时脚本和日志。连接失败或 Demo Mode 时停止等待人工处理，不用模拟结果替代真机。
