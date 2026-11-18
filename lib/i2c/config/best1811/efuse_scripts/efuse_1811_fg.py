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
        #在此处添加读取efuse的逻辑
        
        #使用32M时钟
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 0, 0)
        print(f"写入0xa8 data[0]=1")
        
        #判断0xa9是否为0
        reg_addr = 0xa9
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xa9 = 0x{value:02X}")
        value = (value & 0x001E)
        if value != 0:
            print(f"efuse idle不为0，读取失败")
            return 0
         
        #读操作
        reg_addr = 0xaa+UI_REG_ADDR
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0x{reg_addr:X} = 0x{value:02X}")    
         
        return value
        
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
        data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        #在此处添加写入efuse的逻辑
        #判断0xaa是否为0
        reg_addr = 0xa9
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xa9 = 0x{value:02X}")
        value = (value & 0x001E)
        if value != 0:
            print(f"efuse idle不为0，读取失败")
            return 0
            
        #PMU 1M时钟配置
        dev_addr = 0x17
        reg_addr = 0x2b2
        i2c_interface.write(i2c_speed, dev_addr, reg_addr, 1, data_width, 2, 2)
        print(f"写入0x2b2 data[2]=1")     
        i2c_interface.write(i2c_speed, dev_addr, reg_addr, 0, data_width, 2, 2)
        print(f"写入0x2b2 data[3]=0")
        i2c_interface.write(i2c_speed, dev_addr, reg_addr, 0, data_width, 8, 4)
        print(f"写入0x2b2 data[8:4]=0")
        reg_addr = 0x40
        i2c_interface.write(i2c_speed, dev_addr, reg_addr, 1, data_width, 13, 13)
        print(f"写入0x40 data[13]=1")     
        i2c_interface.write(i2c_speed, dev_addr, reg_addr, 1, data_width, 12, 12)
        print(f"写入0x40 data[12]=1")
        
        #时钟选择
        reg_addr = 0xa4
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 13, 13)
        print(f"写入0xa4 data[13]=1")
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 12, 12)
        print(f"写入0xa4 data[12]=1")
        
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 2, 2)
        print(f"写入0xa8 data[2]=0")
        
        #烧录数据
        reg_addr = 0xa0+UI_REG_ADDR
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, UI_DATA_VAL, data_width)
        print(f"写入0x{reg_addr:X} 0x{UI_DATA_VAL:02X}")      
        time.sleep(0.05/1000)
        
        #使能信号
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 0, 0)
        print(f"写入0xa8 data[0]=1")
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 1, 1)
        print(f"写入0xa8 data[1]=1")
        
        time.sleep(1.2/1000)
        
        #关闭时钟
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 0, 0)
        print(f"写入0xa8 data[0]=0")
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 1, 1)
        print(f"写入0xa8 data[1]=0")
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 2, 2)
        print(f"写入0xa8 data[2]=1")  
        
        reg_addr = 0xa4
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 13, 13)
        print(f"写入0xa4 data[13]=0")
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 12, 12)
        print(f"写入0xa4 data[12]=0")     
                        
        return True
        
    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
