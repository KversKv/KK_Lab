# audioPrecision — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 与 [instruments/AGENTS.md](../AGENTS.md)。本文件仅补充 APx 实机调试的文档加载规则。

## APx525 实机调试必读

- 涉及 APx525 / APx500、Python API、VMware Guest、SSH、共享目录、仪器连接或自动化调试时，开始分析、修改或执行前先阅读 [APx525_VM_AI_Debug_Runbook.md](./APx525_VM_AI_Debug_Runbook.md)。
- 遵循 Runbook 的执行边界：仪器控制程序在 Windows Guest 内运行；主机负责编辑代码并通过 SSH 远程执行，共享目录用于交换代码、日志和结果。
- 排查时先核对 Runbook 中的已确认状态、路径差异和检查步骤，不假设主机能直接控制 APx USB，也不把主机路径当作 Guest 路径。
- 实机运行前确认 USB 直通、APx500 仪器识别、测试项目与授权、信号输出及负载连接；不得覆盖唯一的 APx 测试项目。
- APx500 5.0 PSRR 配置：通道数写 `AnalogInput/AnalogOutput.ChannelCount`，EQ 写 `InputEqChannels[i].Eq="None"`，波形写 `Generator.Waveform="Sine"`；`InputChannelCount`、`InputEq`、`Generator.Type/AnalogType` 不可写。
- `apx_psrr_guest.py` 由 SSH Worker 拼接 `psrr_analysis.py` 与本驱动后执行，依赖拼接后的算法全局函数，禁止当作可独立导入运行的 Guest 脚本。
- PSRR 手动 OUTPUT 与扫频解耦：`configure_psrr_measurement(..., generator_on=None)` 只配置电平并保持当前发生器开关；手动 ON 走持久会话 `output` 命令，扫频不得自动改 ON/OFF，Disconnect 前显式关闭。
