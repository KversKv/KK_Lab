# APx525 实机自动化调试手册

## 目标

在 Windows 11 24H2 主机上使用 Codex/AI 编写和迭代自动化代码；在 VMware 虚拟机内运行 APx500 5.0 与 Python API，连接真实 APx525。代码和日志通过 VMware 共享目录交换，主机通过 SSH 在 Guest 运行命令。

~~~text
Windows 11 24H2 主机
  Codex 编辑代码 ── D:\share\VM ── VMware 共享目录
       │                                  │
       └──── SSH 别名 testvm ─────────────┤
                                          ↓
Windows 10 Enterprise LTSC 2021 Guest
  APx500 5.0 + 对应 Python/.NET API + USB 直通 APx525
~~~

核心原则：**仪器控制程序在 Guest 运行**。共享目录负责传文件，SSH 负责远程执行；APx API 负责通过 APx500 软件控制仪器。

## 当前已确认状态

| 项目 | 状态 |
|---|---|
| 主机 | Windows 11 24H2 |
| Guest | Windows 10 Enterprise LTSC 2021，21H2，Build 19044.6332 |
| 虚拟化 | VMware Workstation |
| Guest 网络 | NAT，Guest IP 为 192.168.208.128；主机 VMnet8 地址为 192.168.208.1 |
| 实机 | Guest 内 APx500 5.0 可运行，用户已确认能执行测试 |
| SSH | 主机运行 `ssh testvm "hostname; whoami"` 成功，返回 DESKTOP-EUPT74V 和 desktop-eupt74v\administrator |
| 端口 | 主机到 Guest TCP 22 可达 |
| 主机共享目录 | D:\share\VM |
| Guest 共享目录路径 | 尚待执行 Test-Path 验证；若共享名是 VM，通常为 \\vmware-host\Shared Folders\VM |
| Guest SSH 安装方式 | SSH 已可用；具体安装来源/版本尚未记录 |

主机端可复核 SSH：

~~~powershell
ssh testvm "hostname; whoami"
Test-NetConnection 192.168.208.128 -Port 22
~~~

预期 Guest 名称为 DESKTOP-EUPT74V、账户为 desktop-eupt74v\administrator，TCP 测试结果为 TcpTestSucceeded : True。

## 1. 确认 Guest 能访问共享目录和 Python

在主机 PowerShell 执行：

~~~powershell
ssh testvm "Test-Path '\\vmware-host\Shared Folders\VM'"
ssh testvm "Get-ChildItem '\\vmware-host\Shared Folders\VM' | Select-Object -First 10 Name"
ssh testvm "py -0p"
~~~

- 第一条返回 True，表示 Guest 能看到主机共享目录。
- py -0p 列出 Guest 已安装的 Python 版本和路径。后续运行时选与 APx API 位数、依赖兼容的解释器。
- 若共享目录返回 False，在 VMware Workstation 的虚拟机设置中启用 Shared Folders，确认共享名为 VM，并确认 VMware Tools/共享文件夹功能在 Guest 中可用。
- 主机目录为 D:\share\VM；Guest 中使用 VMware UNC 路径。两边路径不同，不要把主机的 D:\... 路径直接当成 Guest 路径。

## 2. 建议的项目目录

在主机共享目录中创建：

~~~text
D:\share\VM\APxDebug\
├── project\       APx 测试项目副本
├── src\           Python 自动化代码
├── logs\          运行日志、异常堆栈
└── results\       测量结果、导出文件
~~~

先在 APx500 GUI 中手动准备并保存一份可工作的项目副本，再由 Python API 打开和运行。初期让 AI 修改小范围自动化代码，不要让脚本覆盖唯一的 APx 测试项目。

## 3. 主机编辑、Guest 运行的调试循环

1. Codex 在主机的 D:\share\VM\APxDebug\src 中修改 Python 代码。
2. 从主机 PowerShell 通过 SSH 在 Guest 执行脚本。将 3.11 改为 py -0p 实际列出的版本；将示例文件名替换成你的程序。

~~~powershell
ssh testvm "py -3.11 '\\vmware-host\Shared Folders\VM\APxDebug\src\run_apx.py'"
~~~

3. 脚本将标准输出/错误返回到主机终端，并把详细日志和测量结果写入共享目录的 logs、results。
4. Codex 读取共享目录里的日志、异常和结果，修改代码后重复运行。

建议每次运行都记录：时间、Python 版本、APx 软件/API 版本、项目路径、仪器是否被 APx 识别、执行的 sequence、异常堆栈和结果文件路径。日志由 Python 脚本写入共享目录，避免依赖 SSH 会话退出后仍存在的终端内容。

## 4. APx Python 控制方式

APx500 自动化使用 **APx500 API**。AP 官方的 Python 示例通过 Python.NET 调用 APx 的 .NET API；这不是 PyVISA/SCPI，也不是直接向 USB 端点发命令。

- 使用 Guest 中安装的 APx500 5.0 对应 API 程序集、文档和示例。
- AP API 工具与 APx 软件主版本相关，不能假设 APx 9.x 的封装兼容 APx 5.0。
- 先用 APx GUI 保存项目，再用 API 打开项目、运行 sequence、读取结果，是较稳妥的自动化起点。
- 当前这套流程不需要在 Win11 主机上安装 APx5 API 或尝试直接控制 APx USB 驱动。

AP 官方资料：

- [APx500 Python Guide（官方 ZIP，含指南和示例）](https://www.audioprecision.com/fileadmin-ap/technical-library/APx500_Python_Guide.zip)
- [AP 官方：使用 Python 控制 APx500](https://www.audioprecision.com/blog/controlling-apx500-software-using-python)
- [AP 官方：APx 自动化与 Sequence API](https://www.audioprecision.com/analyzers-accessories/apx-overview/automation)
- [APx500 5.0 用户手册](https://www.audioprecision.com/fileadmin-ap/technical-library/APx500_Users_Manual_v5-0-3.pdf?force=)

## 5. 断点调试

日常迭代可以先用“SSH 运行 + 日志回传”。需要交互断点时，可在 Guest 中安装 debugpy，让它只监听 Guest 本机地址，通过 SSH 隧道转发到主机；不要把调试端口直接开放到外部网络。

一种做法是使用 VS Code 的 Python Debugger attach 配置。主机侧建立隧道：

~~~powershell
ssh -N -L 5678:127.0.0.1:5678 testvm
~~~

Guest 内再启动等待调试器连接的脚本：

~~~powershell
py -m debugpy --listen 127.0.0.1:5678 --wait-for-client "\\vmware-host\Shared Folders\VM\APxDebug\src\run_apx.py"
~~~

在 VS Code 中附加到主机 127.0.0.1:5678。若源码位于主机与 Guest 不同路径，需要配置本地/远程路径映射；或者直接用 VS Code Remote-SSH 打开 Guest 中的项目路径。

## 6. 实机连接检查

运行脚本前确认：

1. VMware Workstation 的 USB 菜单把 APx525 连接到 Guest（Disconnect from Host）。
2. Guest 设备管理器识别 APx 设备，APx500 GUI 能识别仪器，而非 Demo Mode。
3. APx GUI 中先单独运行已保存的测试项目，确认项目和授权正常。
4. 首次运行自动化时用低风险、已知的测试项目和连接方式；确认信号发生器输出、被测设备和负载符合实验室设定，再运行完整 sequence。

若 Guest 中 APx GUI 看不到仪器，优先检查 USB 是否已直通到 Guest；SSH 成功只证明网络和远程执行通道正常，不证明 USB/仪器通道正常。VMware 的 USB 直通会将设备交给 Guest，Host 和 Guest 不能同时占用同一 USB 设备。[Broadcom USB 直通排查说明](https://knowledge.broadcom.com/external/article?legacyId=1008576)

## 7. 常见故障定位

| 现象 | 检查方向 |
|---|---|
| ssh testvm 找不到主机 | 主机 SSH 别名/配置文件；本机 PowerShell 已验证可用 |
| Connection refused | Guest 的 SSH Server 未运行或端口未监听；检查 Get-Service sshd 和 TCP 22 |
| Permission denied | Guest 用户名、密码/密钥及 SSH 用户授权 |
| 共享目录 Test-Path 为 False | VMware Shared Folders、共享名、VMware Tools；Guest 路径不是主机 D:\share\VM |
| SSH 成功但 APx 找不到仪器 | VMware USB 直通、Guest 设备管理器状态、APx 驱动 |
| APx GUI 可测但 Python API 报类型/程序集错误 | Python 位数/依赖、API 程序集路径、API 与 APx5 主版本是否匹配 |
| 脚本运行但无结果 | 项目路径、sequence 状态、API 返回值、日志/结果目录权限 |

## 8. 关于当前 SSH 安装问题的记录

Guest 的 D:\ 是卷标为“不忘初心系统”的 Windows 启动安装介质，不是 OpenSSH Features on Demand（FoD）源；搜索该盘也没有找到 OpenSSH-Server-Package*.cab。Guest 的 OpenSSH Capability 曾显示 Staged，即文件已暂存但功能未安装。

虽然 Windows Update 在线安装曾返回 0x8000ffff，目前用户的 ssh testvm 已成功执行远程命令，因此远程调试通道已可用；不需要为了当前自动化流程继续重复同一安装命令。若以后重装 Guest 的内置 OpenSSH，Windows 10 LTSC 2021/21H2 应使用与 Windows 10 2004 及以后版本对应的 FoD 来源，或按微软文档检查“可选组件安装和组件修复”的 Windows Update/WSUS 策略。[微软 OpenSSH 安装排查](https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/cant-install-openssh-features) [微软 FoD 版本对应表](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/features-on-demand-v2--capabilities?view=windows-11)

## 9. Codex 当前会话的执行边界

用户本机 PowerShell 已能通过 SSH 别名 testvm 远程执行命令。当前 Codex 工具环境不能读取该用户的 SSH 配置文件，因此它无法直接复用该别名；这不影响 Codex 编辑共享目录代码、也不影响用户在主机 PowerShell 执行 SSH 命令。

不要把 SSH 私钥内容粘贴到聊天。若要让 Codex 在工具环境中直接运行 Guest 命令，需要为该执行环境提供受控的 SSH 配置/凭据访问，或由主机本地启动脚本作为受控执行入口。

## 来源

- Audio Precision：APx500 Python Guide、API 自动化文档和 APx 5.0 用户手册（见上方链接）。
- Microsoft：[OpenSSH 安装和配置](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)；[OpenSSH Features on Demand 故障排查](https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/cant-install-openssh-features)。
- VMware/Broadcom：[USB 设备无法在虚拟机中使用的排查](https://knowledge.broadcom.com/external/article?legacyId=1008576)。

