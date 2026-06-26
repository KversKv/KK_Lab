# 1307PH SOC PMU Module Test Report

## 关机漏电



## 开机波形

设计预期:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2EyYjg1Mjk1NmZlMDg4OGJiY2M0M2QyMzJlNTc5NDlfMWExZjdmNWFlNDA0ZGY5MjcyNjNhNTQ2MmZjOGFlNThfSUQ6NzYyMjg2Nzk2ODMwOTMzMjk1MV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODdiMTAyNTg1MGZiMzg0YjQyZTlkNGNhNTk0NzFiZmNfMmE0YjRlMzAxZDIzMjJlMDZhNGNkOTU3NTgzOTgzOTFfSUQ6NzYyNDM2MDU2NjIzMzAwOTExOF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



## 开机Vbat瞬态电流

波形图片：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzMyMjk4OTljYTBmMTRiOGVkOGY1MzlkMDc0NjMxZWFfMmQ5OTg4ZDFjZGQ1NzgwZjBhYjc5OTE2MzE4MDY3NDFfSUQ6NzYyNDM2MTUxOTY2MDk3NzA4Ml8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



## RST电流以及波形

高电平持续时间9\.911ms, 低电平恢复时间14\.345ms;

波形:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTNhMzRlNjg4NjQ1NzNkNzM3YzdhY2EwZjRhMDIyOWZfMjk1ODIzZGY3YWQxOTExNmRlMjI4ZDBmMzEwZjNjZDlfSUQ6NzYyNDM3NDkyNjE4Mjg3ODEzOV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

## AC\_ON

## 开关机电压\(UVLO\)

## Powerkey及漏电

Poweron \& RST  **PIN 脚耐压值**

POWERON \& RESET 耐压值为2\.5V; VBAT耐压值5V

内部下拉电阻5M

## RST电平

内部阻抗约为460k

## 关机波形

a\) soft poweroff  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NjliYjk4NzgyNjQ3OGJlZGM5NGIzMmU5MTNjNmNlZmVfMTJmYjIwY2M1ODdiYTU2YWViNGVlN2RkZjk5MGRhN2NfSUQ6NzYyNDQxNjU0OTUyNTE0NjU4N18xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

b） 快速关机\+soft poweroff  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTg5ZGY0NTRhNTU5YWY1MzUxMDlhMzFlMmIxNWViOTJfNTUyODUwZDFhNWRhOTk3MmRhMGE0ZDUwN2ZhY2I2ZDBfSUQ6NzYyNDQxNzIwNzQyNjEwODYxNV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

支持快速关机，掉电时间大幅降低7s \-\> 8ms

## 带载能力和纹波测试\(normal\)

SIMO测试

### BUCK\_VCORE :  最大带载200mA

同1307P, 强制PWM, 默认不更改任何配置:

\[BES2711IUC2\_BUCK\_VCORE\_is\_gainAndRipple\_Test\_screenshots\.rar\]

\[BES2711IUC2\_BUCK\_VCORE\_is\_gainAndRipple\_Test\.xlsx\]



\[BES2711IUC2\_BUCK\_VCORE\_is\_gainAndRipple\_Test\_screenshots\.rar\]

\[BES2711IUC2\_BUCK\_VCORE\_is\_gainAndRipple\_Test\.xlsx\]

### BUCK\_VHPPA: 最大带载200mA

考虑交叉调制会导致纹波变大, 需要实测确认是否有影响;

\[BES2711IUC2\_BUCK\_VHPPA\_is\_gainAndRipple\_Test\_screenshots\.rar\]

\[BES2711IUC2\_BUCK\_VHPPA\_is\_gainAndRipple\_Test\.xlsx\]



\[BES2711IUC2\_BUCK\_VHPPA\_is\_gainAndRipple\_Test\_screenshots\.rar\]

\[BES2711IUC2\_BUCK\_VHPPA\_is\_gainAndRipple\_Test\.xlsx\]







由于单电感双输出, 因此输出存在切换,会导致纹波偏大, 如果不考虑切换造成的过冲, 平均纹波可以降低一半\(上述记录的纹波都是带有过冲的纹波\), BUCK\_VCORE=10mA, BUCK\_VHPPA=50mA:





### LDO\_VANA: 最大带载150mA

实测带载200mA, Drop27\.4mV; 根据场景判断是否能用;



### LDO\_VMIC1: 最大带载30mA

当前VMIC纹波大, 是由于VMIC依赖VCM\_CAP, VCM\_CAP依赖BUCK\_VHPPA\. BUCK\_VHPPA纹波较大;

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YjQ0MDRkMDQwZTEwODU4NzAyMjBjMjUwODM3Y2ZjZjZfMTQ5MTYyNDg2NmNkMmM5ZDU0MzJmYzlmZDU1MzViN2RfSUQ6NzYyNzM5MTI2OTE2NzM1MzAxM18xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)







## 带载能力测试\(dsleep\)



## GPIO

### 开机脉冲

**pass**代表开机时GPIO电压小于50mV,且没有毛刺

### 驱动能力

[1307PH DCDC效率\&GPIO驱动能力](https://hhkspse03v.feishu.cn/wiki/U8NBwZ90pi9ypWkulpJcTjeonRc?sheet=V1Jhct)



输出阻抗：



## PATTERN 复位

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OGU3YTg5YThlMzFkYmEwZjdjMmUzMDQ1N2FiYzQ5MTlfZTY2YjkwZjQyNzNjNGEzZmM1ZjhhMGE4NzhkZTI1MThfSUQ6NzYyNDQzNTEyMjQzNjAxNzM3NF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

## 静态电流

1307系列 DCDC 没有 ULP mode ;
1307PH只有一个VMIC;

睡眠状态时, Mic只能使用LP模式; 

## LDO PSRR



## SPK短路保护

ocp\_sel

达到限流持续1ms;1307PH正常1K Hz最大音量平均负载为39mA@1\.8V, 峰值电流61\.6mA, 最低档存在误触风险\.

## DCDC效率

[1307PH DCDC效率](https://hhkspse03v.feishu.cn/wiki/U8NBwZ90pi9ypWkulpJcTjeonRc)

测试时, 另外一路带载5mA, 待测的一路BUCK输出负载1\~200mA Ramp;



## GPADC测试

### GPADC CH0 Temperature:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWRlNjZkNWEzNTA2NmMyYmQ2ZWJkOGVkN2VmYTdmZjJfMGEwNjA5OGMwNzI4YjMyNzNmMWU3M2MwMDkwMGY4Y2RfSUQ6NzYyNjIwNzgyODQ2MTUwNTQ2NV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)





### GPADC CH1 VSYS DIV4:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWUzNDg5ZmY4NDE0NTJjOTYwNTQ4NzQxNDVmMDc5ZjlfM2U3ODJkNmFkYzk4YjE3NTdiZGIzYWYzYmRiZDM1ZjFfSUQ6NzYyNTkxMjcxMjkwODAzMjk3OF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)





### GPADC CH3 EXT1:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmYwMTA3Y2Q5MTRmY2QzMjVhZTBmNzk2OWQ1MjFiNzFfZjZkNzJiYmE2NDE0ODA5YjkwNDJlYjI5ODI5NmI5ZDBfSUQ6NzYyNTkxMDYxNTMwNzkxNDQzMV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)





## 各个LDO输出电压所有挡位







## 各个DCDC输出电压 所有挡位

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzRjZmYxMjE1MDc2NjU0OTYzNWQ1NWIwMmY4NWI3NzBfNTFhMGI2YzRmYjEwMDhkZWRjZTU2YjUxZGQwNGYwNjBfSUQ6NzYyNDQ1MjAwMzU2MDgzNjAzOF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2ZlNGYxNGVlMWUxNzU5NmI4YTNmM2VkOWI0MWM3MTJfMTY4MWRlYWNjNjI3MTQ3ZDY5Mzc2ZmY0MGVhYzcxOTZfSUQ6NzYyNDQ1MTY4MzQxMDAyMTMyMV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)







## DCDC不同负载电感电流 



## 负载快速变化的瞬态响应

负载从1mA\-100mA切换, 依次为10Hz \\ 100Hz \\ 1000Hz





## DCDC线性调整率\& LDO线性调整率

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MWY5NzBkNThhNTU0ZWZiOGY2ZDllZDdkMWY2ZjJmZjFfYjEyYmNmZWZiNTYxZmM5MTFiNDNkZjk5NGZlOWRhMmJfSUQ6NzYyNDQ5ODM4MTY0Mjg0NTM2NF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

## 电源输入瞬态响应

3\.2V\-4\.2V 10Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OGVjYjE0MjU2OTk0YjIyMzVhMzVjNGZhNmE0ZTg5NjBfODQ4ODYyNTM1OWQ5YmIyMDA3ZGI3ZThkMTNiNThhMTdfSUQ6NzYyNDQ5NzYyMDg5MTc4MjA3Nl8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

3\.2V\-4\.2V 50Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDdkYzIxNWM2MmVjNTdlMGRlNjU0MjZkNzM4MWIxMjFfZTFlMTMzY2M0MGQxY2FiNjU5YWY1OWI2NGE2MmZlNDdfSUQ6NzYyNDQ5NzcwNzU5MTU2ODU3M18xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

3\.2V\-4\.2V 100Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTEwZjEzOWJjNjI5YzM0ZTdkNjIyMmM2MzViOWQyZmRfZjRhOTA3NDU2MTM2NmQwNzVkYTBhYmNiZjU3ZDc4NjFfSUQ6NzYyNDQ5Nzk5MzY5NzY2MDA5OV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

3\.2V\-4\.2V 1000Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjEyNDBhZDQzNDNiM2U1YzAzZmViNzcyNTBlN2RjNGZfMDAwZGJlNGYwZjc3ZjcwY2UzMmQ5NTIzZWJmOTNhMGZfSUQ6NzYyNDQ5ODA2MDE4NTM0MDg4OV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

## BUCK 死区时间

默认dt\_bit=0为8\.913ns;dt\_bit=1为9\.256ns

## buck 各档位频率

目前使用同步时钟

## buck 各档位edge上升时间





## BUCK   各档位IS\_GAIN、阈值

1307PH强制PWM使用









## Vbat悬空时，AC\_IN接5V，测VSYS 电压

不带路径管理, 插入5V\_IN, Vbat为Voreg电压\(4\.184V\), 默认4\.184V\. 充电时 Vbat = 电池电压





## 休眠电流

## 单线通讯

921600  通信正常;

## 休眠唤醒电压差

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MjI2NmU3YTBjMWRiNDQxNmQ4OGEwZjZkNzI4YWViNjNfMDE1NDlkZWQ5ODA1Yjk1MGNhZDMzMjE5NWYwYzAzZGFfSUQ6NzYyNjU5ODYwMTA4NjcxNjg3OV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWVlZDlmYzE2Y2VkODVjNWMyOTY4MWVmZDBkNjM0MjNfZWU5ODgzY2Y2MzQ1NjQzMjMyZjRhNmUyMDAxZGIwNGNfSUQ6NzYyNjU5ODYyODc0OTQ3ODg4MF8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDhiYjJhMDY4YWIwNDc5MGI2ZmJiZjNjMDY4YzI0NzFfNDc4YzJmYTBmY2VjNzkxNDBmZTg2MjJlMTJjZjIxZDhfSUQ6NzYyNjU5ODY0NDQwMTM3NjQ1MV8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTk0NjJlYWQwNjYxNDJhZDQ4NWEwZWFhZjM4M2U5OTlfMjY4NDQwODBkYTJlNjkxZGUwNTBjZjgwY2RiYmE5YmNfSUQ6NzYyNjU5ODYxMDM1Nzc4MzQ5Ml8xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



## AC\_ON开关机测试

1000次未见开关机异常



## 上电Latch Up

Vbat和ACIN 快速上电20次未见Latch Up现象\.



## LX 可靠性测试

### LX 负压测试

测试时, LX电感断开, Vsys=3\.8V, 限流200mA; AC\_IN Ramp负电压, 限流150mA;

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzU4MjczOTI5N2Y4NmJjZmFhMDVmM2UxZjI0NTY5OGJfNzRjOGFkNmQxOWNlOThlM2MwYjdjNDU1OTFiNmVhMzhfSUQ6NzYyNjY4ODk2MDQwODA5NTcwN18xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)

在LX = \-1V 时, 测掉负压, Isys大电流没有保持







## VMIC底噪测试

测试比1502P坏片好, 不如1811的VMIC性能,满足使用标准\.

\[vmic\_test0414\_1307PH\.approjx\]

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDhjZTIwNTQ5Zjk1NzE1ZDI1MGNiNWUyODJlNDIwNWJfMTlhMTMwMjljODA1NmI5MzkyOWQzNjEyM2UyZjUzYzFfSUQ6NzYyODU0NjY5NDAyMzk1NzY5N18xNzgyNDQzMTQ2OjE3ODI1Mjk1NDZfVjM)



