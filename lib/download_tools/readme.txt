
Parameter introduction:
Serial port configuration: 12
Serial port baud rate    : --pgm-rate 921600 
Full Erase Flag			 : --erase-chip 
Write the magic code at the specified address: -m 0x2c018000
Burn the bin at the specified address : --addr 0x28000000 test.bin
Burn bin and magic code    :  -M test.bin
Configuration programmer   : --ramfile .\programmer.bin 
Configure log file         : --save-log timeout.txt
Configure power-on timeout (milliseconds): --timeout 2000
config bootloader          : --bootloader
Configure application files: --appbinary .\app.bin
Configure Bluetooth address: --btaddr EABD4A001244
Configure the peer address : --peeraddr EABD4A001244 
Configure ble name         : --blename bleName
Configure ble address      : --bleaddr EABD4A001245
Configure Bluetooth name   : --btname bestest  
Configure frequency offset value file  : --btcalib 127
Configure dual flash : --set_dual_chip 1

支持的参数介绍:
配置串口参数          : --port 12
配置下载过程波特率    : --pgm-rate 921600 
配置芯片全擦除        : --erase-chip 
配置指定地址写入magic : -m 0x2c018000
配置指定地址下载文件  : --addr 0x28000000 test.bin
配置下一个文件写入magic    :  -M test.bin
配置芯片programmer    : --ramfile .\programmer.bin 
配置下载log保存文件   : --save-log timeout.txt
配置上电握手超时时间  : --timeout 2000
配置boot loader 文件  : --bootloader
配置芯片 app 文件     : --appbinary .\app.bin
配置蓝牙地址          : --btaddr EABD4A001244
配置配对对儿蓝牙地址  : --peeraddr EABD4A001244 
配置ble 名称          : --blename bleName
配置ble 地址          : --bleaddr EABD4A001245
配置蓝牙名称          : --btname bestest  
配置rf 频偏值 		  : --btcalib 127
配置后续操作dual 模式 : --set_dual_chip 1

外置存储，文件系统方式写入文件
6 programmer.bin --emmc --nand-fs /data/emmc0/target_file.bin sourcefile.bin
6			：comm 串口号
programmer 	：master新编译支持文件系统操作版本
--emmc		： 标识外置emmc 介质
--nand-fs	： 标识下一个参数是文件系统路径。带mount的路径
sourcefile.bin ：源文件。

外置存储，物理地址方式写入镜像
6 programmer.bin --emmc --addr 0x0 sourcefile.bin
6			：comm 串口号
programmer 	：master新编译支持文件系统操作版本
--emmc		： 标识外置emmc 介质
--addr		： 标识下一个参数是emmc 存放地址
sourcefile.bin ：源文件。

注意：
外置存储类型参数： --emmc --sd --spi-nand --ufs

工厂区配置示例
注意:
工厂区需要 --appbinary 参数指定 app 文件来获取芯片分区信息，工具才能写入nv factory数据到正确的位置
Example:
.\DldTool.exe  12 .\programmer.bin  .\boot_ota.bin  --appbinary .\app.bin.  --btaddr EABD4A001244 --peeraddr EABD4A001244 --btname bestest  

支持根据 Jason 文件配置内容，执行下载流程。
配置格式参考 dld_cfg-demo.json 文件。
usb 下载，需要配置usb usb_connect true。
外置存储介质不同，需要配置 memory type 选项，配置说明参考 dld_cfg-demo.json 文件
使用方式：
dldtool.exe --dld-cfg dld_cfg.json 

