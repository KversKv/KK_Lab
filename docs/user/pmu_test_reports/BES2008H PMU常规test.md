# BES2008H PMU常规test

区别于别的芯片, BES2008系列, Vsys供电严禁超过3\.3V;

## 关机漏电



## 开机波形

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDhhZjJkNDc4YWZkZjk1NTg0MDc3MTg0NDMzZTM2ZjVfMzAyODk3ODg3ODg1MjVlZmEyZGQyZWU4ZTY2NTAyMjlfSUQ6NzQ2MjMzNzM4MTQ1NDkzODE0MF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)





## 开机Vbat瞬态电流

波形图片：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGFiNGE0ZTBiYjA1MGNkZTc2MmQ2NTNkZDI2YzUwOGZfMjI5N2UzZTU3ODA0ODNlNWRmY2NiZmRjMTFkYjRhYzBfSUQ6NzQ2MjMzOTcwNjI3NDIzNDM3MV8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



## RST电流以及波形

波形

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Yzc2NDVjNWZjODYwMzA4NmI0YTc0NGVjNjZiOTZjY2RfMzViNjE0ODk1ZDE4ZDJmNTdkZWVjNDBkNTIzNmI0YmNfSUQ6NzQ2MjMzNzQzNjUwNjA5NTYzNV8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)

## AC\_ON

## 开关机电压

## Powerkey及漏电

Poweron \& RST  **PIN 脚耐压值**

## RST电平

## 关机波形

a\) soft poweroff  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmU4ZGRiMjlhMTAxNzY0MTJhYjM2ZGNmYTNkNGQ1NjZfZmI0NWYzMmQzZTU5ODkzNjViMjM3NmQ0N2NkYTcyMjlfSUQ6NzQ2MjMzNzU0MTc2NTkyMjgyMF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)

## 带载能力测试\(normal\)



**DCDC**

2008H DCDC 唤醒固定PWM模式



LDO 



## 带载能力测试\(dsleep\)





## BG切换电源输出压差

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2Q5ZDlhMGIzZTQwZDFjMWUyMDhmNGI3ZjFhMjBjZjJfZTViYTQ3YzJmNjMxNjdiNzUxNWVlMmNkNGExMTMzNmZfSUQ6NzQ2MjM1MDQ0NDA3ODQ4MTQyN18xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)

## GPIO脉冲及电平

**pass**代表开机时GPIO电压小于50mV,且没有毛刺

## PATTERN 复位

08和08H不支持PATTERN 复位



## 静态电流



## LDO PSRR





## DCDC PSRR



## buck纹波



## LDO纹波





## DCDC效率

[BES2008H DCDC效率](https://hhkspse03v.feishu.cn/wiki/TCRWwNq1SigHgMkf9j3cmD6dn9C)

## GPADC测试

FT校准、软件 GPADC burst mode下 ；需要复测；

ADC\_Vref 上电时间/纹波/带载







高低温GPADC2\_channel

稳定性测试





## 各个DCDC输出电压 所有挡位

[BES2008H电源输出电压范围](https://hhkspse03v.feishu.cn/wiki/PQAXw1RDYib25WkQ0SccROWanIf?sheet=e051aa)

## 各个LDO输出电压 所有挡位

[BES2008H电源输出电压范围](https://hhkspse03v.feishu.cn/wiki/PQAXw1RDYib25WkQ0SccROWanIf?sheet=e051aa)



## DCDC不同负载电感电流





## DCDC线性调整率\& LDO线性调整率

2008H限定VBAT=3\.3V使用



## 负载快速变化瞬态响应

### BUCK\_VCORE

10Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzVhNjU4ZTBiM2MwOWYxZmNmZjAzMTZkN2E1ZDZhMTdfZmI5YjU0NmQyZDMzMTFiZDY3NjU2Y2NjYzE2ZDkyMDBfSUQ6NzQ2MzM3MTI2MTg4OTI4MjA1MF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



100Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzkyZGZkOWU4ODQ3NGQ3NmQ2YjBlZTBkNDE5ODlkZTJfOTg5NDU4NTQ3NzUxN2Q2MmQ1ZGRiMTgwY2E1ZjdkNzlfSUQ6NzQ2MzM3MTEyOTc2NDM4MDY3NV8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



1000Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjJkZGFkZDI4ZjhmMDUwNWZiNGFhMzVhZTIwZmZhNjlfYmU3ZDY0YWM1ODY2MTNmNjYwMGY5MTk2Y2MzMDhlMDJfSUQ6NzQ2MzM3MDgxODcyMTI4NDA5OV8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



### BUCK\_VANA

10Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Njc4M2RlODlhZWUyZDUyNWFkMDUzZTgxOGNjMzMyY2VfYTUzMDYyY2U0NTJiYjM0YWJiNGIyYWUzZDQzMThlODFfSUQ6NzQ2MzM3MDMzNDk4MTgzMjczMl8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



100Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWNmNjRlYjAyMDJjZmQ3MTI2ODBhOWIzNGIyNTUwZjVfOWU4YTBkY2U3ZjIxZWU5NzZiN2Q3MDI1MThmZDA5ODlfSUQ6NzQ2MzM3MDQ3Njc0MDkwMjkxM18xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



1000Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDkwNjY3MTBkMWFiZTQ2MzMwODRjZTVhYTY3Y2RkZGRfZWM4MzM0MTdlNTk4ZDA4NDk0ZWJlOTk2NGU5MDQ2ZWVfSUQ6NzQ2MzM3MDYwMzAwMzY1ODI2OF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)





### BUCK\_VIO

10Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmZjZWQzNmVmNzQ5MTgwOTZjMmVmMDVmOTNkMDNmMWZfYTEyNWU2ZWExMThjMjBkYjk0NzhmMzU0NTc4ODBjYzNfSUQ6NzQ2MzM2OTg4NDIzMjM2ODE1Nl8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



100Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=M2MxNzQyYzhlZTI2Y2Y1MWZkYjA5N2RmY2Q4OGQ5ZjRfZjEyZGZhMjEzYjRjOWE3MTU1MDgzODY5NjU1NzNjODdfSUQ6NzQ2MzM2OTY5MjQ2Nzg1NTM4OF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



1000Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzA0YjNmNjVlNzg1NjAwN2QwODcxMzliYmU2NmU2OTBfYTNjYTBjNDI3NmYzYTM1YTE3MjVlMGMxNzY4NDE2ODRfSUQ6NzQ2MzM2OTA2MjUzNjA1Mjc0MF8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



## LDO输入瞬态响应

### LDO\_VIO

10Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmVlNGMwNjc4YjdjZWRkMTFmZTQ5ZDQ4YzE2MmI2YzdfZWNiMWFlNTcxZDNkZTE1OWRlMmRhM2QzZTFjMGE2YzNfSUQ6NzQ2MzM2ODIxNzU2MzE1MjQxMl8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



100Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTAyN2MzYTU3MzQ0YWQyYzVhOTQ0Mjc5MjMzMmFkNDJfOTE5ODBmMjBkMDVhMTAwOTIyNmUwMzcxNTE5NzcxMWFfSUQ6NzQ2MzM2ODM2NDIyOTI5NjE1Nl8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)



1000Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTkxY2RkN2U4NDY1NmFmMzY0MDNkNWNjODc0ZDdiMDVfMjFlNTE3NzdkYTkwMDgyMWMwZGQ4NjI1M2RlODc4ZDRfSUQ6NzQ2MzM2ODUzOTE3MTgxNTQyN18xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)





## 内部电源切换测试

只有BUCK\_VIO存在DCDC和LDO的切换

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzgzNjRiNWZmMDUyZTZjNzdhNmQ0ZDQ2NzVlZTBkNTRfZmMzNTkyMWIzZDIzMDhhNWI2NjJmYzZmYzQ3ZmUwMTNfSUQ6NzQ2MzAzNjI2NDQ1NzI4OTczMV8xNzgyNDQzNjQwOjE3ODI1MzAwNDBfVjM)

## Vcore\_L\&M Bypass阻抗

## BUCK 死区时间

## buck 各档位频率



## buck 各档位edge上升时间





## BUCK   各档位IS\_GAIN



## Vbg、VRTC、ADC\_VREF 各档位电压

## 休眠电流

## 休眠唤醒电压差

受到大小bg切换影响





