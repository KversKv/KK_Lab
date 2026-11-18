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
#i2c_interface.write(i2c_speed, UI_DEV_ADDR, UI_REG_ADDR, ui_data_val, data_width, high_bit, low_bit) #写入位
#---------------------------------------------------------------------------------------#
import time


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

    try:
        i2c_speed = I2CSpeedMode.SPEED_100K
        data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        #在此处添加读取efuse的逻辑
        #判断0x1af[11:8]是否为0
        reg_addr = 0x1af
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0x1af = 0x{value:04X}")
        if (value & 0x0f00) != 0:
            print(f"efuse idle不为0，读取失败")
            return 0

        #切换efuse时钟为osc，此段时钟切换步骤也可不执行，使用32K时钟读efuse
        reg_addr = 0x1b1
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print(f"写入0x1b1 data[14]=1")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 2, 2)
        print(f"写入0x1b3 data[2]=1")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 9, 9)
        print(f"写入0x1b3 data[9]=1")

        time.sleep(50/1000000)

        #开启efuse clk en, read mode
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0008
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 0x0008")

        #打开function turn on
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0018
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 0x0018")

        time.sleep(100/1000000)

        valuelist = []
        for i in range(0,4):
            efuse_addr = UI_REG_ADDR*4+i

            #读取单个efuse
            #写入address[6:0] 仅address 7位有效
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0018 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次read trigger
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0038 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次read trigger关闭
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0018 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #addr clear
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0018
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            time.sleep(20/1000000)

            #读取数值，8位data
            reg_addr = 0x1af
            value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
            print(f"读取0x1af = 0x{value:04X}")
            valuelist.append(value & 0xff)

        final_data = (((valuelist[1]<<8) & 0xff00)+(valuelist[0]&0xff)) | ((valuelist[3]<<8 & 0xff00)+(valuelist[2]&0xff))

        #关闭读 function turn off
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0008
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

        #关闭clk
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

        #切换efuse时钟为32k
        reg_addr = 0x1b1
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print(f"写入0x1b1 data[14]=0")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 2, 2)
        print(f"写入0x1b3 data[2]=0")

        return final_data

    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return -1
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return -1


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
        data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        #在此处添加写入efuse的逻辑
        #判断0x1af[11:8]是否为0
        reg_addr = 0x1af
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0x1af = 0x{value:04X}")
        if (value & 0x0f00) != 0:
            print(f"efuse idle不为0，写入失败")
            return False

        #切换efuse时钟为osc
        reg_addr = 0x1b1
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print(f"写入0x1b1 data[14]=1")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 2, 2)
        print(f"写入0x1b3 data[2]=1")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 9, 9)
        print(f"写入0x1b3 data[9]=1")

        time.sleep(1/10000)

        #文档中修改reg_write_cnt的0x1aa/9'd59步骤已划掉，此处不执行

        #开启efuse clk en, pgm_mode selected
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 0x0009")

        #打开function turn on
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0019
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 0x0019")

        time.sleep(100/1000000)

        group_page_size = 32 // 8
        first_in_group = UI_REG_ADDR * group_page_size
        low_8  = UI_DATA_VAL & 0x00ff
        high_8 = UI_DATA_VAL & 0xff00

        for i in range(0,16):
            if ((low_8 >> i) & 0x1):
                efuse_addr = (i << 7) | (first_in_group)
            elif((high_8 >> i) & 0x1):
                efuse_addr = ((i - 8) << 7) | (first_in_group+1)
            else:
                continue

            #写入单个efuse
            #Write data= {bits[2:0],address[6:0],6'b01_1001})
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0019 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次write trigger
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0039 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次write trigger关闭
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0019 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            time.sleep(2/10000)

            #备份区域
            efuse_addr = efuse_addr + 2

            #Write data= {bits[2:0],address[6:0],6'b01_1001})
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0019 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次write trigger
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0039 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            #单次write trigger关闭
            reg_addr = 0x1a8
            data_need_to_be_written = 0x0019 | (efuse_addr << 6)
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

            time.sleep(20/1000000)

        #关闭写 清空地址/function off
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

        #关闭efuse clk, pgm_mode
        reg_addr = 0x1a8
        data_need_to_be_written = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0x1a8 = 0x{data_need_to_be_written:04X}")

        #切换efuse时钟为32k
        reg_addr = 0x1b1
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print(f"写入0x1b1 data[14]=0")

        reg_addr = 0x1b3
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 2, 2)
        print(f"写入0x1b3 data[2]=0")

        return True

    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
