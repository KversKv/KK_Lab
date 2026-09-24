# ------------------------------------------------------------------------------
# 在 I2C Tool 中执行 eFuse 脚本
# ------------------------------------------------------------------------------
i2c_interface = globals().get('i2c_interface')
I2CSpeedMode = globals().get('I2CSpeedMode')
I2CWidthFlag = globals().get('I2CWidthFlag')
I2CError = globals().get('I2CError')

# 检查注入的UI值是否存在并打印
UI_DEV_ADDR = globals().get('ui_dev_addr') # 获取注入的设备地址
UI_REG_ADDR = globals().get('ui_reg_addr') # 获取注入的UI寄存器地址
UI_DATA_VAL = globals().get('ui_data_hex')         # 获取注入的UI数据值
UI_DATA_WIDTH = globals().get('ui_data_width') # 获取注入的UI数据宽度
prefix = globals().get('ui_module_name_unique') # 获取注入的chip name+模块名称
ui_chip_name = globals().get('ui_chip_name') # 获取注入的芯片名称
# ------------------------------------------------------------------------------
#i2c读写接口可用模块
#I2CSpeedMode.SPEED_100K #100K
#I2CWidthFlag.BIT_8 # BIT_8 8位 BIT_10 16位 BIT_32 32位
#i2c_interface.read(i2c_speed, UI_DEV_ADDR, UI_REG_ADDR, data_width) #读取寄存器
#i2c_interface.write(i2c_speed, UI_DEV_ADDR, UI_REG_ADDR, ui_data_val, data_width) #写入寄存器
#i2c_interface.write_bit(i2c_speed, UI_DEV_ADDR, UI_REG_ADDR, ui_data_val, data_width, high_bit, low_bit) #写入位
#---------------------------------------------------------------------------------------#
import time

#def read_efuse_1702(reg_offset: int) -> int:
def read_efuse(reg_offset: int) -> int:
    """

    Args:
        reg_offset (int): 要读取的eFuse内部地址/偏移量

    Returns:
        int: 读取到的数据

    Raises:
        I2CError: 如果I2C通信失败
        Exception: 其他意外错误
    """
#---------------------------------------------------------------------------------------#
    # 读寄存器脚本demo
    # print(f"尝试读取eFuse地址/偏移量 0x{reg_offset:02X}")
    # data_width = I2CWidthFlag.BIT_8
    # i2c_speed = I2CSpeedMode.SPEED_100K

    # # 此处简化为直接从一个假设的地址读取 (请替换为真实逻辑)
    # value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_offset, data_width)

    # print(f"从eFuse地址/偏移量 0x{reg_offset:02X} 读取到值: 0x{value:02X}")
    # return value
#---------------------------------------------------------------------------------------#

    try:
        i2c_speed = I2CSpeedMode.SPEED_100K
        data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        #efuse idle判断0d0[03:00]是否为0
        # reg_4008e0d0_addr = 0x4008e0d0
        # reg_4008e0d0_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_4008e0d0_addr, data_width)
        # print(f"读取0x4008e0d0 = 0x{reg_4008e0d0_data:02X}")
        # if reg_4008e0d0_data != 0:
        #     print(f"efuse idle不为0，读取失败")
        #     return 0

        #开启efuse clk en，read mode
        reg_4008e004_addr = 0x4008e004
        reg_4008e004_data = 0x40000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 0x00040000")
        time.sleep(0.005/1000)

        #打开 function turn on
        reg_4008e004_data = 0x60000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 0x00060000")
        time.sleep(0.005/1000)

        #Write data=  {16’h0006,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]}
        efuse_addr = UI_REG_ADDR
        reg_4008e004_data = 0x60000 | efuse_addr
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 16’h0006,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]")

        #单次read trigger
        #write addr=(ADDR_base+32'h0000_0004)
        #Write data=  {16’h0007,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]}
        reg_4008e004_data = 0x70000 | efuse_addr
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 16’h0007,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]")
        time.sleep(0.002/1000)

        #单次read trigger关闭
        #write addr=(ADDR_base+32'h0000_0004)
        #Write data=  {16’h0006,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]}
        reg_4008e004_data = 0x60000 | efuse_addr
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 16’h0006,3’b000,bits[4:0],{UI_REG_ADDR}[7:0]")

        reg_4008e000_addr = 0x4008e000
        reg_4008e000_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_4008e000_addr, data_width)
        print(f"读取0x4008e000 = 0x{reg_4008e000_data:02X}")
        time.sleep(0.002/1000)

        #关闭读
        #清空地址/funtion off write addr=(ADDR_base+32'h0000_0004) Write data=32'h0004_0000
        reg_4008e004_data = 0x00040000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 32'h0004_0000")
        time.sleep(0.005/1000)

        #关闭efuse clk,  write addr=(ADDR_base+32'h0000_0004) Write data=32'h0000_0000
        reg_4008e004_data = 0x00000000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, data_width)
        print(f"写入0x4008e004 32'h0000_0000")

        final_data = ((reg_4008e000_data & 0xffff0000) >>16) | (reg_4008e000_data & 0xffff)

        return final_data

    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return -1  # 返回错误码
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return -1  # 返回错误码


#def write_efuse_1702(reg_offset: int, data: int, high_bit: int = -1, low_bit: int = -1) -> None:
def write_efuse(reg_offset: int, data: int) -> bool:
    """
    Args:
        reg_offset (int): 要写入的eFuse内部地址/偏移量(也可以使用UI_REG_ADDR)
        data (int): 要写入的数据(也可以使用UI_DATA_VAL)

    Raises:
        I2CError: 如果I2C通信失败
        Exception: 其他意外错误
    """

    try:
        i2c_speed = I2CSpeedMode.SPEED_100K
        ui_data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        # efuse idle判断0d0[03:00]是否为0
        # reg_0x40080d0_addr = 0x4008e0d0
        # reg_0x40080d0_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_0x40080d0_addr, ui_data_width)
        # print(f"读取0x4008e0d0 = 0x{reg_0x40080d0_data:02X}")
        # if reg_0x40080d0_data != 0:
        #     print(f"efuse idle不为0，写入失败")
        #     return False

        #开启efuse clk en，pgm mode
        reg_4008e004_addr = 0x4008e004
        reg_4008e004_data = 0x240000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
        print(f"写入0x4008e004 0x240000")
        time.sleep(0.005/1000)

        #打开 function turn on
        reg_4008e004_data = 0x260000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
        print(f"写入0x4008e004 0x260000")
        time.sleep(0.005/1000)

        #get Addr and Reg Addr;
        data_to_be_written = (UI_DATA_VAL<<16) + UI_DATA_VAL
        for i in range(32):
            efuse_addr = UI_REG_ADDR
            reg_4008e004_addr = 0x4008e004
            if ((data_to_be_written >> i) & 0x1) == 1:
                #写入单个efuse
                #write addr=(ADDR_base+32'h0000_0004)
                #Write data=  {16’h26,3’b000, bits[4:0], address[7:0]})
                reg_4008e004_data = 0x260000+efuse_addr+(i<<8)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
                print(f"写入0x4008e004 16’h26,3’b000, bits[4:0],{efuse_addr}[7:0]")

                #单次write trigger
                #Write data=  {16’h27,3’b000, bits[4:0], address[7:0]})
                reg_4008e004_data = 0x270000+efuse_addr+(i<<8)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
                print(f"写入0x4008e004 16’h27,3’b000, bits[4:0],{efuse_addr}[7:0]")
                time.sleep(0.010/1000)

                #单次write trigger关闭
                #write addr=(ADDR_base+32'h0000_0004)
                #Write data=  {16’h26,3’b000, bits[4:0], address[7:0]})
                reg_4008e004_data = 0x260000+efuse_addr+(i<<8)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
                print(f"写入0x4008e004 16’h26,3’b000, bits[4:0],{efuse_addr}[7:0]")
                time.sleep(0.002/1000)
            time.sleep(0.5/1000)

        #关闭写
        #清空地址/funtion off write addr=(ADDR_base+32'h0000_0004)
        reg_4008e004_data = 0x00240000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
        print(f"写入0x4008e004 0x00240000")
        time.sleep(0.005/1000)

        #关闭efuse clk, pgm mode
        reg_4008e004_data = 0x00000000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_4008e004_addr, reg_4008e004_data, ui_data_width)
        print(f"写入0x4008e004 32'h0000_0000")

        return True

    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
