# audioPrecision — 局部 AI 协作指引

> 就近生效，继承根 [AGENTS.md](../../AGENTS.md) 与 [instruments/AGENTS.md](../AGENTS.md)。本文件仅补充 APx 实机调试的文档加载规则。

## APx525 实机调试必读

- 涉及 APx525 / APx500、Python API、VMware Guest、SSH、共享目录、仪器连接或自动化调试时，开始分析、修改或执行前先阅读 [APx525_VM_AI_Debug_Runbook.md](./APx525_VM_AI_Debug_Runbook.md)。
- 遵循 Runbook 的执行边界：仪器控制程序在 Windows Guest 内运行；主机负责编辑代码并通过 SSH 远程执行，共享目录用于交换代码、日志和结果。
- 排查时先核对 Runbook 中的已确认状态、路径差异和检查步骤，不假设主机能直接控制 APx USB，也不把主机路径当作 Guest 路径。
- 实机运行前确认 USB 直通、APx500 仪器识别、测试项目与授权、信号输出及负载连接；不得覆盖唯一的 APx 测试项目。
