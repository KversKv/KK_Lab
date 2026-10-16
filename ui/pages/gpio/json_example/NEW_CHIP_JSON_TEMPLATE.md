# 新芯片 GPIO JSON 配置 — 信息采集模板

> **用法**：复制本文件后改写，把 `【】` 占位替换为实际值；用不到的可选段整段删除即可。
> 填好后把整份文件发给 AI，AI 会据此生成 `chips/gpio_configs/<chip>.json` 并自检。
>
> - 参考成品：[chips/gpio_configs/bes1701.json](../../chips/gpio_configs/bes1701.json)
> - 解析规则（AI 已掌握）：[core/gpio/gpio_config.py](../../core/gpio/gpio_config.py)

---

## 0. 前置硬约束（芯片寄存器模型必须满足，不满足请在文末"备注"里说明）

- bank 内寄存器偏移固定：Out Set=+0x00 / Dir Set=+0x04 / Out Clr=+0x0C / Dir Clr=+0x10 / Input Read=+0x50
- 每 bank 32 个 GPIO（4 group × 8 pin），bank 内 bit 序 = (group%4)*8 + pin
- 寄存器位宽固定 32bit
- I2C 设备地址 **不在** JSON 里配置（自动取 `chip_info["main_die_i2c_addr"]`，0x11/0x31 自适应）

## 1. 必填信息

### 1.1 芯片名

`【besxxxx】`

> 必须与 `bes_chip_check()` 返回的 `chip_name` 一致；JSON 文件名 = 芯片名小写 + `.json`。

### 1.2 GPIO banks（每行一个 bank，按 Group 升序）

| bank 名 (name) | bank 基地址 (base) | 有效 group 数 (groups，可选，缺省 4) |
| -------------- | ------------------ | ------------------------------------ |
| 【AON_GPIO0】  | 【0x40081000】     | 【4】                                |
| 【AON_GPIO1】  | 【0x40089000】     |                                      |

> - `groups` 仅当该 bank 高位 group 物理不存在时填 1~3（如仅 18 group 的芯片，末 bank 填 2）。
> - bank 数 = 总 group 数 ÷ 4 向上取整。

## 2. 输入上下拉（可选；芯片无上下拉则整段删除）

- pull_up_bases（与 banks 平行的地址表，每 bank 一个 32bit 寄存器、1bit/GPIO；某 bank 无 PU 则对应位置填 null）：
  `【0x40086084, 0x40086088, 0x4008608C, 0x40086090, 0x40086094】`
- pull_down_bases（同上）：
  `【0x40086098, 0x4008609C, 0x400860A0, 0x400860A4, 0x400860A8】`
- pull_ohm（上下拉阻抗 Ω，仅 UI 显示，可不填）：up = `【36437】`，down = `【35517】`

## 3. 输出驱动强度 drv（可选；无 drv_sel 则整段删除）

寻址方式 **二选一**（删掉另一种）：

- **A. per-group 显式地址表**（地址区不连续时用，如 BES1701）：
  drv.group_bases（按 Group0..N 顺序，每寄存器 8 脚）：
  `【0x40086060, 0x40086064, ...】`
- **B. 线性区**（地址连续时用）：drv.base = `【0x40086060】`
  （bits_per_gpio=2 → 每寄存器 16 脚；=4 → 每寄存器 8 脚）

公共字段：

- bits_per_gpio：`【4】`（只允许 2 或 4）
- levels：档位总数，缺省 = 2^bits_per_gpio，需要截断时填：`【16】`
- out_high_ohm / out_low_ohm：各档位输出阻抗表（Ω，仅 UI 显示，可不填；索引 = 档位值）：
  `【1463.4, 756.9, ...】`

## 4. func_sel 引脚复用（可选；GPIO 无需选功能则整段删除）

- base：`【0x40086004】`（线性排布：地址 = base + (脚序 // 每寄存器脚数) × 4）
- bits_per_gpio：`【4】`
- gpio_value：选为 GPIO 功能时 sel 位域要写的值：`【0xF】`
- groups：有效 group 数上限，0 = 不限制：`【18】`
- functions（iomux 复用功能表，可不配；不配则 UI 不显示功能名/无 Set Function 菜单）：
  直接把 **datasheet 的 iomux 表整段粘贴**在这里（Excel 复制的表格/文本均可，AI 负责转换为
  `"GPIO_P{group}_{pin}": [Func_0..Func_N]` 格式，list index = sel 位域值，未用值补 null）。
  若有现成 xlsx（如 BES1701 的 `Temp/bes1701_iomux.xlsx`），也可只给文件路径，AI 写脚本注入。

  【在此粘贴 iomux 表】

## 5. 备注（异常/特殊点，没有则删除）

【如：某 bank 偏移不符合第 0 节硬约定、drv 位域排布特殊、某些脚不支持某功能等】

---

## 6. 生成后验收清单（AI 生成 JSON 后逐项过）

1. `chips/gpio_configs/<chip>.json` 语法合法、`gpio_banks` 非空；
2. 页面 Detect DUT 后自动加载该配置，Matrix 显示的 bank/group 数与实际一致；
3. 任挑一脚：输出高/低 + 输入回读正常；配了 drv/pull/func_sel 的各验证一次。
