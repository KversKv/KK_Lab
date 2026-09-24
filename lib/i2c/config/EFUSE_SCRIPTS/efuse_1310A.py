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
UI_DATA_VAL = globals().get('ui_data_hex') # 获取注入的UI数据值
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

        # 判断0x158是否为idle
        reg_addr = 0x158
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0x158 = 0x{value:02X}")
        if (value & 0xf) != 0:
            print("efuse idle不为0，读取失败")
            return 0

        # 切换efuse时钟为osc，0x147 data[14]=1'b1
        reg_addr = 0x147
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print("写入0x147 data[14]=1")

        # 开启efuse clk en、read mode
        reg_addr = 0xb7
        data_need_to_be_written = 0x0008
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print("写入0xb7 0x0008")
        time.sleep(5/1000)

        # 打开function turn on
        reg_addr = 0xb7
        data_need_to_be_written = 0x0018
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print("写入0xb7 0x0018")
        time.sleep(5/1000)

        # 写入address[3:0]，读操作中bits[4:0]为0
        efuse_addr = UI_REG_ADDR
        reg_addr = 0xb7
        data_need_to_be_written = 0x0018 | (efuse_addr << 6)
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

        # 单次read trigger
        reg_addr = 0xb7
        data_need_to_be_written = 0x0038 | (efuse_addr << 6)
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
        time.sleep(2/1000)

        # 单次read trigger关闭
        reg_addr = 0xb7
        data_need_to_be_written = 0x0018 | (efuse_addr << 6)
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

        # 0xbd和0xbe分别读取32bit data的高、低16bit
        reg_addr = 0xbd
        value1 = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbd = 0x{value1:02X}")

        reg_addr = 0xbe
        value2 = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbe = 0x{value2:02X}")
        time.sleep(2/1000)

        # 延续1307PH模板：高低16bit按正常值/备份值合并显示
        final_data = value1 | value2

        # function turn off
        reg_addr = 0xb7
        data_need_to_be_written = 0x0008
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
        time.sleep(5/1000)

        # 关闭efuse clk
        reg_addr = 0xb7
        data_need_to_be_written = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

        # 切换efuse时钟为32k，0x147 data[14]=1'b0
        reg_addr = 0x147
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print("写入0x147 data[14]=0")

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

        # 判断0x158是否为idle
        reg_addr = 0x158
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0x158 = 0x{value:02X}")
        if (value & 0xf) != 0:
            print("efuse idle不为0，写入失败")
            return False

        # 24M时钟使能
        i2c_interface.write(i2c_speed, 0x11, 0x40080004, 1, I2CWidthFlag.BIT_32, 28, 28)
        print("写入0x40080004 data[28]=1")

        # 切换efuse时钟为osc，0x147 data[14]=1'b1
        reg_addr = 0x147
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print("写入0x147 data[14]=1")

        # 开启efuse clk en、pgm mode
        reg_addr = 0xb7
        data_need_to_be_written = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print("写入0xb7 0x0009")
        time.sleep(5/1000)

        # 打开function turn on
        reg_addr = 0xb7
        data_need_to_be_written = 0x0019
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print("写入0xb7 0x0019")
        time.sleep(5/1000)

        # UI输入为16bit业务值，按1307PH模板扩展为正常值和备份值后扫描32bit
        gui_data_to_be_written = (UI_DATA_VAL << 16) + UI_DATA_VAL
        for i in range(0, 32):
            if ((gui_data_to_be_written >> i) & 0x1) == 1:
                # address[3:0]=UI_REG_ADDR，bits[4:0]=i
                efuse_addr = UI_REG_ADDR + 16*i

                # 写入单个efuse
                reg_addr = 0xb7
                data_need_to_be_written = 0x0019 | (efuse_addr << 6)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

                # 单次write trigger
                reg_addr = 0xb7
                data_need_to_be_written = 0x0039 | (efuse_addr << 6)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                time.sleep(10/1000)

                # 单次write trigger关闭
                reg_addr = 0xb7
                data_need_to_be_written = 0x0019 | (efuse_addr << 6)
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                time.sleep(2/1000)

        # 清空地址、function turn off
        reg_addr = 0xb7
        data_need_to_be_written = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
        time.sleep(5/1000)

        # 关闭efuse clk、pgm mode
        reg_addr = 0xb7
        data_need_to_be_written = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

        # 切换efuse时钟为32k，0x147 data[14]=1'b0
        reg_addr = 0x147
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print("写入0x147 data[14]=0")

        return True

    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
