# BES1811 PMU 测试项汇总

本文档主要是针对PMU特性的测试项, 由于1811是功能复杂且完善的PMU, 因此还有其它单独的测试报告:

1. Bring Up 记录清单: [BES 1811 Bring Up ](https://hhkspse03v.feishu.cn/wiki/WuLYwxDUfiRsQYkcQdxc5NflnHc?sheet=mAWUJt)

2. BES1811 PMU常规测试项:  [BES1811 PMU常规测试项](https://hhkspse03v.feishu.cn/wiki/Y7uWwL4BYiKJztk1ZqfcAR2fnme)

3. BES1811 DCDC Buck\&Boost测试项: [1811 BUCK Test](https://hhkspse03v.feishu.cn/docx/BwbldVX3joUJXjx388scfpUWnLd?from=from_copylink)

4. BES1811 LDO测试项: [BES1811 LDO测试结果](https://hhkspse03v.feishu.cn/wiki/XjHHwb0t1iDbolk8CGTcN6XZnBg)

5. BES1811 Switch Mode Charger测试项: [1811 switch mode charger 功能验证](https://hhkspse03v.feishu.cn/wiki/R8jOw1FhxiNDTAkxMzwcPTL5nuh?from=from_copylink)

6. BES1811 Fuel Gauge:  [1811 Fuel Gauge 功能验证](https://hhkspse03v.feishu.cn/wiki/MJmhwp1lQieJLYklb9gczUm5nDf?from=from_copylink)





## 关机漏电

当前使用低电平开机, 上表结果去掉电阻分压导致的电流, 4V对应2uA漏电;

高通5100关机电流50uA;Ship\_mode是6\.7uA;

## 开机波形

仿真波形:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmUxMzExMzU3NmQ2NzJiYjYxY2RjZjkxYjE0NjljZGZfMWE3MTYwODJhZWQ3NmY5MDM2NTM2YjBhNmI5YzJkYzhfSUQ6NzYwMjI2OTI5NTU2OTM0MTM3OV8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

实测波形:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDk5MWYzNGJmYTM4NDRkNWIyMGQ4YjgyNzY4ZWJhNzBfMDM2MzNmNDI4ZDcxZGEwZjJhNWU5OTgyYTYwODgyMjlfSUQ6NzYwMjE1MDI5NDMxNTYwMTA5MF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MjViZjFhMTQyOTdjN2E1ZDczYjg2YmFiZjczYTMxOGNfYjI5ZThhYmUxMDU3ZTg4MjdlNmVmYzA0ZjZmZDAxODBfSUQ6NzYwMjE1MzIyNDQzNDg2MzMwMF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)









## 开机Vbat瞬态电流

最大的峰值电流为 60mA; 

仿真开机电流波形如下:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YTg5NGZiMGRlZmM2MzcyYWU0NzgxZmEwNjY3NzMzNTlfNmRiZjI0YjA0MGI1Y2Y3ZDZkZDY5ZDk0YWZkNDkxZTZfSUQ6NzYwMjQ1NjAxNDU1NDQ1MTE3Ml8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

实测开机电流波形如下:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YmZkZDg4ZmQyMDJlODlhODdlODZjNzM3Y2ViNTQwMzZfNGJiNGVlN2Y2MDBlZGE5ZGY1ZGNiZjM3MTYxNTZhN2JfSUQ6NzYwMjE1ODAyNDk0MTY1Mjk1MF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGJjNGJhZWEzY2M4YmRiZmMwNDZjZWY5NTE2MzEwMzRfODkyODEwMmY1NThlNjY3NDg2MmMyOGJiNGJjNWU0M2RfSUQ6NzYwMjE1ODQwNjgxMjQ4Njg3NF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzJmZjYzZDM1NWU2M2U2Mjk4MGM1ZThmYWM4MWIxOTNfOTZhMzI1NjM3MzU1OGI0ZDZiODQzMzRmNDQxMWRiODdfSUQ6NzYwMjQ1NjI3Njk2NjU0MjI4N18xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)





## RST电流以及波形

Reset波形如下:

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmU2YWMwOWUwMjQzNDAwMTI5MWYwMDQ4NzYyMTFjNjFfZjZlYjZiYzliMGJjNTFkMDkwMjNiZTM3Yjc0ZmNhODZfSUQ6NzYwMjQ1NjIyOTIzOTQ5MTU0NF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)



## UVLO测试

VBAT电压从4V突变到0\.5V\~2V一颗暂未发现未关机现象;



## AC\_ON

VCHG\_G阈值电流6\.2uA,  芯片端钳位3\.8V;





## Powerkey开机 阈值\&漏电

PWR\_KEY\&REST 耐压都为5V;

VBAT\&VSYS 耐压都为5V;

VCHG\-R耐压为5V;
CHG\_IN耐压为16V;









## RST电平

1811 RESET新增功能, 长按800ms以上, Charger会Reset芯片;  //FT是否考虑测试, 以及分布;  需要限定客户高电平时间\.



reset\_chip 1MOhm;  reset\_chip阻抗和bd\_option没关系；

bd\_option=0,power\_on阻抗是7\.5M，bd\_option=1，输入是管子的gate阻抗很大\.



## 关机波形

1811 soft poweroff  自带pulldown 逻辑  

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWQxY2NlNmMyZjkwYTQ2YWZmMmViNDBjZDE5ZTliYjZfODA5NWJjYTFiOGU0N2JkY2MxNTM5NjZlNTM3Yjc1MWJfSUQ6NzYwMjUyMzMyNDYzNTc0NTQ3OF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)



## 单线通讯（单封芯片暂未测量）





## PATTERN 复位

在VCHGR输入特定pattern后可以看到三路电发生复位

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTMwM2JmY2E2NjI5NDkzMzEzZjgzZGQwYmQ2MDQ3OWVfMDIzZTQ3MzhhMGM5NzMzNWY1MWMxMDNjNzg3YmU2OWRfSUQ6NzYwMjUyNjExMzcwOTAzNDQyNV8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)





## GPADC测试

耐压最高2\.5V\(理论上可以到Vbat\);  

输入范围0\~1\.8V;

[BES1811 LDO输出电压范围\&GPADC](https://hhkspse03v.feishu.cn/wiki/PdcGwtVAeiXl4EkdAjocLnUVn6e?sheet=KDBSSd)

### Channel 0: Temperature

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWYyN2MxMjVmNGNjMmIzMDVmNTU1ZDQzOTU3YzRhYjhfMmI3MDcwMzA2NmVlNzMzMjRmNjhmYzQ3YWYyOWZkZjJfSUQ6NzYyMzk3NzI3NjAwNjk3NjcxNl8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)

Thermal gain=2'b10:



Thermal gain=2'b01:







### Channel 1: VSYS:  DIV4



### Channel 2\~5: External 0\~3



### Channel 6\~9: External 4\~7



### Channel 10: VBAT:  DIV4



### Channel 11: VCHG\-MID:  DIV4



### \(3\)\. 高低温测试一致性

ExtADC0 \-\> Internal ADC2






## LPO

### 默认频率

### 频率范围

20\.82kHz\~75\.67kHz     

### JITER

37\.72k

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2Q1OTg5YjM1MjAxYzk2ZWE2MzVjODU2NTUyNWUxMzBfNjVmYzgzOTRiMGRkMzdiMTMzNjcyYmExYTE2NTM3ZDhfSUQ6NzYwMjU0MTc2Njk5OTA1MTQ2NF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)



100次软件频偏测试



### 高低温



### 休眠唤醒频偏



### DCDC干扰测试

Charger, 大功率条件测试



## 外部32K晶体

### PowerSel：

### Capbit：

默认Capbit: 9'b 1\_0010\_0000, 对应频率是32\.764617kHz

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OThlMjQ0MDFiYzcyYTllN2UzMGNlNjFlMzg4MTU3NmRfY2QwZjhlNmFhNGI4ZmNhOWIyMTFmYjIyNTc1NWI0OTdfSUQ6NzYyNDA3NjIxNzY1ODU3NTgzMF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)



### 静态功耗：



### 高低温： 



![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDBkYjQ5ODA2MGI0NTkxM2NlMGE0ZjQwZmU5MDYyYTdfNmZlZjE0MWE2ZTFhOTZkZDliMjUwOTgzNWE1MWEyNDNfSUQ6NzYyNDM0OTcyODI5MzkxNTgzNF8xNzgyNDQyOTU4OjE3ODI1MjkzNThfVjM)





### PMU重载对XO\_32K的影响: 

BUCK1\~2负载10mA:  32\.7795kHz;

BUCK1\~2负载100mA:  32\.7794kHz;

BUCK1\~2负载1A:  32\.7796kHz;

BUCK1\~2负载2A:  32\.7756kHz;

BUCK1\~3负载100mA\< \- \>1\.5A切换, 频率分布不变;





## DVFS（待测）

至少要看控制功能和时序





## PMU Interface

单封芯片和1605搭配, 初步验证下来PMU和Charger的SPI功能均正确\.



## Latch Up相关测试

Vbat快速上电50次未见Latch Up;

Vsys快速上电50次未见Latch Up;

充电过程中, 5V\_IN突然短路测试;

Vbat3\.8V,  AC\_IN, VSY直接抽电流负载, 是否出现LatchUp;
补充LX\(包括ChargerLX\)抽负电流

## 开关机撞沿测试

AC\_ON给50Hz \(0\~5V\) 方波, 不断写soft\_power\_off:

1. 未出现无法开机的情况;

2. 出现无法关机的情况, 同3601P, 已知问题, 依赖软件WDT重启;



## 静态电流vs温度













## QFN 睡眠电流分析

### 关机电流拆分

\#1

\#2



### 睡眠电流拆分

\#1

\#2





\#3  外供1\.8V测试\(由于Flash\&PSRAM静态电流大\)





## EFUSE 读写

EFUSE读写验证正常, 读写脚本如下:

```Markdown
OSC_WRITE_EFUSE_0_Data1:
- WRITE_BITS 0x01B1 14 14 0x1
- WRITE_BITS 0x01B3 2 2 0x1
- WRITE_BITS 0x01B3 9 9 0x1
- // reg_write_cnt
- WRITE_BITS 0x01AA 8 0 0x3b
- DELAY 10
- WRITE 0x01A8 0x0009
- WRITE 0x01A8 0x0019
- DELAY 10
- //addres
- WRITE_BITS 0x01A8 12 6 0x0
- // data
- WRITE_BITS 0x01A8 15 13 0x0
- DELAY 10
- WRITE_BITS 0x01A8 5 5 0x1
- DELAY 10
- WRITE_BITS 0x01A8 5 5 0x0
- WRITE 0x01A8 0x0009
- WRITE 0x01A8 0x0


 
OSC_READ_EFUSE_0:
- //READ Result at 0x01AF
- WRITE_BITS 0x01B1 14 14 0x1
- WRITE_BITS 0x01B3 2 2 0x1
- WRITE_BITS 0x01B3 9 9 0x1
- DELAY 10
- WRITE 0x01A8 0x0018
- //ADDRES
- WRITE_BITS 0x01A8 12 6 0x0
- //READ Trigger
- WRITE_BITS 0x01A8 5 5 0x1
- DELAY 10
- WRITE_BITS 0x01A8 5 5 0x0
- WRITE_BITS 0x01A8 12 6 0x0
- DELAY 10

32K_READ_EFUSE_0:
- //READ Result at 0x01AF
- WRITE_BITS 0x01B1 14 14 0x0
- WRITE_BITS 0x01B3 2 2 0x0
- WRITE_BITS 0x01B3 9 9 0x0
- DELAY 10
- WRITE 0x01A8 0x0018
- //ADDRES
- WRITE_BITS 0x01A8 12 6 0x0
- //READ Trigger
- WRITE_BITS 0x01A8 5 5 0x1
- DELAY 10
- WRITE_BITS 0x01A8 5 5 0x0
- WRITE_BITS 0x01A8 12 6 0x0
- DELAY 10

```



## LED Function验证\(待测\)

功能, 占空比, 频率范围;是否独立可调





## GPIO测试\(待测\)



