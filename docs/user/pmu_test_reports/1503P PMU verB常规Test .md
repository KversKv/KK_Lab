# 1503P PMU verB常规Test 

# Bring Up 汇总

1. LDO限流偏小, 

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDZmZThmNzE5MjM1MjJkNTM4NWMwOGIzOTNhOGVhODBfNjJjZDI2ZmUzNGUzNzVhMTY0MjU5Y2YxMWIyNTUzMmNfSUQ6NzU2ODMyNDAyMTc0ODI2OTA2MF8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)





## 关机漏电



## 开机波形

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MjQ5NjlmMGZhZGJiOGEwM2QwMmU2YTFhYzMxYzRmNmFfODk4NTMzNTk4NGZmYjRiM2I5MzNjYmFmNDI5MGY1ODNfSUQ6NzU2ODMyNDAyMzc4NTYzNTg0M18xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



## 开机Vbat瞬态电流

波形图片：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGFhZGZkMDczYzc3ZmVjYzFkNWQxNjhhOWU1YTI4ODNfNWRiMDdlMjRhOTMyNWY4YzExZWY4MTllYjRjOGIwMDZfSUQ6NzU2ODMyNDAyNTI4NzA0OTIxOV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



## RST电流以及波形

波形

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmIwNTc0NWJhNTkyZWY0YTNkMWQzMDU3YWE0NDE0ZmVfMGE3MzU0MTc0ZDQ1YWM3MGI2MDhmNGU1OGViYzBkNjRfSUQ6NzU2ODMyNDAyMTc0ODQwMDEzMl8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)

## AC\_ON

## 开关机电压

## Powerkey及漏电

Poweron \& RST  **PIN 脚耐压值**

POWERON \& RESET 耐压值为2\.75V; VBAT耐压值5\.5V

内部阻抗约为5M\(高电平开机的方式\)

## RST电平

内部阻抗约为0\.5M

## 关机波形

a\) soft poweroff  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTA4MzgwNTY2NTNkZGMzMDA1ZmNhZDY5Njc3NmEwM2NfYmJjN2Q5MjJhMDlkNGE3YzBlOTI3OGY5YzFkMGEyMzlfSUQ6NzU2ODMyNDAyMzM0ODAzNTU4N18xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



b） 快速关机\+soft poweroff  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjE5YTgzNTQ4YzlhOTE4MDlmNWU3M2YxZjhmYTNiZjhfZDM5ZjlmMTQzNTBkYmZiYThhNDExYzAyMGI0ZDk0MmJfSUQ6NzU2ODMyNDAyNDc4MTE5MzIzNV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)

支持快速关机，掉电时间大幅降低

## 带载能力和纹波测试\(normal\)

**DCDC**



DCDC高低温纹波

BURST MODE

PWM MODE





BURST MODE \+ 大BG



LDO 

默认LDO有限流保护, 因此默认带载能力有限,详见测试case37



## GPIO

### 开机脉冲

**pass**代表开机时GPIO电压小于50mV,且没有毛刺

GPIO23:


![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDNiOWZkZjM1YzJhYjhmYWNlYzhlOWEzYWNiYzNhYmRfOTA3MTI5OTIzNTc2ZjA4NWY3MjJhZmRhNmRmMWIxMDdfSUQ6NzU2ODMyNDAyMjE0MzY4MDUxNl8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



GPIO34:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTZmMjAzZDBlYzE4ZjRjNjgxNDI3YjE2YmE5NmEwMGRfNDcyMThmY2YzNWQyMjdhMzkwNTZiMmUzOTUzYzI0NjZfSUQ6NzU2ODMyNDAyMTQ4MDc1MTEwN18xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



GPIO36:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDE3NTYzYmU4ODI4OTU0NmI3NTBmNGFkNmU5NGEwZjBfZmYxNDQ4NDQwMTZjYWIwYmVlOTFkM2RjYmUzMzc2ODJfSUQ6NzU2ODMyNDAyMjcyOTQ1NzY2OF8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



GPIO42:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzVlYzc1YWZmMTU0Y2I5OWQzZTNkNmY4M2Y0ZGE0NzBfNmFjYWRkOGZlMTJhZjMxNDYwYTRhYWViNjI2YzNkN2JfSUQ6NzU2ODMyNDAyMTc5NDI0MjU3OV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



GPIO72:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDFjNTNlMWEzOGFjNzIyYmE3MTcxZjdhNzE4MGRlODhfN2QwMTg1MWVhMzhhYWUxMTZiNjU3MmUzNTNmMTEyYTFfSUQ6NzU2ODMyNDAyMzQ1ODgyNDE5NV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)

GPIO96:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWVjNTg0NzA3NmU1MmEwNDA2NjA4NzQwZjgyMzc4NWRfODgxYjhiZmY1NTgwMzdiZmI3ZjA5NDY3NTBkOTZhNjhfSUQ6NzU2ODMyNDAyMzc4NTc1MDUzMV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)





### 驱动能力

设计值:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTg2MWU3MzhjNWU2OTAxYWE0NzE2MGRiOWJlZWY4YjhfMWY1ZTcxMjI3ZDhiMjhjMDZkYTg4YTFjOTc2NjYxMjNfSUQ6NzU2ODMyNDAyNDg2NTA3OTI5OV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)







输出阻抗：



## PATTERN 复位

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzEyOGE3YWU2ZWM5YTY5YzM5YTk4MzJjZGViMGRkNmRfY2I3MGQ1Y2E3Mzk4MzVlMTIzM2ZlMzM1N2NiMTUzZmZfSUQ6NzU2ODMyNDAyMjcxNzIzNTIxOV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)

## 静态电流

## LDO PSRR





## DCDC PSRR





## SPK短路保护

ocp\_sel

达到限流持续1ms;1307P正常1K Hz最大音量平均负载为39mA@1\.8V, 峰值电流61\.6mA, 最低档存在误触风险\.

## DCDC效率

[1503P DCDC效率](https://hhkspse03v.feishu.cn/wiki/JWEzwOl2xiIdYEkYgzncVRplnId?sheet=Sty7wV)

## GPADC测试









10000次读数稳定性测试:



## 各个LDO输出电压所有挡位

[1503P输出电压范围](https://hhkspse03v.feishu.cn/wiki/DiTwwDAPuiWRRIk4GQXc0AZ1nbe)

## 各个DCDC输出电压 所有挡位

[1503P输出电压范围](https://hhkspse03v.feishu.cn/wiki/DiTwwDAPuiWRRIk4GQXc0AZ1nbe)



## DCDC不同负载电感电流 





## 负载快速变化的瞬态响应

负载从1mA\-100mA切换, 依次为10Hz \\ 100Hz \\ 1000Hz





## DCDC线性调整率\& LDO线性调整率

LDO:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODM3ODcyY2YyMGIyMGRkODU5NDkxNGMxMmVlNzU4YzJfNjJmMDVkNjYxYTIyZjY3NTc2MTFiNGMzOWJlZTgxYzRfSUQ6NzU2ODMyNDAyMzA5MDM0ODA1MV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



DCDC:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmU0YjFkODU1MTM1YTAwZDBmNWIxYjE1NTAwZmRhNjBfNmYwNGE3MTdhZGVmMjY5ZjQ1Mjk4YTZjYWE0NTc3NDJfSUQ6NzU2ODMyNDAyNDc4MTM3MzQ1OV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



## 电源输入瞬态响应

3\.2V\-4\.2V 10Hz:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODNhYzgyMTM3OTVmNDEwYzQ4MGRiYWM1OWMyZTM0MzNfYzhmYTI3OTJlZGMwMTYwYTM5NmU0YTY3ZGI2MTFjYTBfSUQ6NzU2ODMyNDAyMTcxMDU2OTQ5MV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



3\.2V\-4\.2V 133Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWZmZGM1OGY3YmU1YzdlZjZiZTdlNTIwMmFiYmNmYjNfNTJkY2ZjMGM2M2EzOTA4ZDVhNmE2OGI4NzJiNmVlOTNfSUQ6NzU2ODMyNDAyMzM0ODQ2MTU3MV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



3\.2V\-4\.2V 800Hz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OTk4NWMyNzVjMmRhNzJiNGE0Yjk1OTY2MGMyOTgyNTFfNjBlMmNmZGNjMGJiZDM0MWE0Y2IwMjQxYTEwZGM2YzdfSUQ6NzU2ODMyNDAyMzI4Njg0MTM0OF8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)





## BUCK 死区时间

默认dt\_bit=0为7\.3ns;dt\_bit=1为8\.7ns

## buck 各档位频率

目前使用同步时钟, 固定1\.715M  =  24M/2 / \(5\+2\)



## buck 各档位edge上升时间



## BUCK   各档位IS\_GAIN

### IS\_GIAN

1503P需要带载能力和阈值校准\.







## 休眠电流

## 单线通讯

BES2720IMP未出单线通信口;



**~~默认波特率921600 3\.3V/1\.8V通信无异常:~~**

**~~波特率1152000 3\.3V/1\.8V通信无异常:~~**

**~~波特率2000000 3\.3V通信无异常; 1\.8V无异常\(需要加强外部上拉电阻到10K\):~~**

## 休眠唤醒电压差

### verA:

休眠到唤醒:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDlhZmM2OTFmNjI1OGZmYWMxODk5NjFlZTgzNGMyMTBfYWRhNjU3MDRjZDU1ZDAyYzkxNzMwNGU2MjE0OWMzZDhfSUQ6NzU2ODMyNDAyMjQxMTUyNjE0OF8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)

唤醒到休眠:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzFjMTA3MzRmMDUxNjIwOTFlMTlkYzc1ODNmZWRmNzlfNWM3YWVhZjcxM2UyZWM4NzdkYmZhYjZkMzdlYmRiMmRfSUQ6NzU2ODMyNDAyMjQxMTQ5MzM4MF8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



### verB 0\.6V:

休眠到唤醒:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODllZDg5MjdlMmY2MTg2ZjVhY2VlMjg2MmU0YjM0ZjBfNzdlZmVlMzM5MmQ0NTA4ZTU3YmUzYTk3NTZmM2E3MTJfSUQ6NzU2ODMyNDY5MDQ4MDgyNDMyMV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



唤醒到休眠:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWY3YjgyYWE1NGMxZWFiNDYzZjIzNjA2NmRiMWM1NjBfYTc4YzE4ZjM4ODVlNmUyMjYzYjExZmZlZDlhZjgzNTFfSUQ6NzU2ODMyNDcwMjIyNTQ0ODk2MV8xNzgyNDQzMDcyOjE3ODI1Mjk0NzJfVjM)



A版存在 1503P调整电压的过程中LDO\_VCORE\_L存在过冲和掉坑现象, 波形具体见:

[1503p ldo\_vcore\_L 掉坑](https://hhkspse03v.feishu.cn/wiki/BXBxwQploikrkhk9BUyciSE1n5g)

B版存在两个版本:

1. 0\.6V版本, BUCK\_VHPPA直接给Vcore0P6使用, 无过冲和掉坑问题, 可以分电使用\.

2. 1\.8V版本, 兼容之前设计, 不推荐分电使用\. 



## AC\_ON开关机测试

100次未见异常



## 上电Latch Up

Vbat和ACIN 快速上电20次未见Latch Up现象\.



## OCP 阈值



## bypass阻抗



