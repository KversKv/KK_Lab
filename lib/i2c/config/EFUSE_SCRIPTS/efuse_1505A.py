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

        #在此处添加读取efuse的逻辑
        #判断0xbe是否为0
        reg_addr = 0xbe
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbe = 0x{value:02X}")
        if (value & 0xf)!= 0:
            print(f"efuse idle不为0，读取失败")
            return 0

        #切换efuse时钟为osc 0xbf data[14]=1'b1
        reg_addr = 0xbf
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print(f"写入0xbf data[14]=1")
        
        #开启efuse clk en,read mode write addr=(10'hb7) Write data=16'h0008
        reg_addr = 0xb7
        data_need_to_be_written = 0x0008
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 0x0008")
        
        #打开function turn on write addr=(10'hb7)Write data=16'h 0018?
        reg_addr = 0xb7
        data_need_to_be_written = 0x0018
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 0x0018")
        
        time.sleep(0.1/1000)
        efuse_addr = UI_REG_ADDR
        reg_addr = 0xb7;
        data_need_to_be_written = (0x0018 |( efuse_addr<<6))
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                    
        #单次read trigger write addr=(8'hb7) Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1000})
        reg_addr = 0xb7
        data_need_to_be_written = 0x0038 |( efuse_addr<<6)
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
        
        #单次read trigger关闭 write addr=(8'hb7) Write data= {efuse_sel,bits[4:0],address[3:0],6'b01_1000})
        reg_addr = 0xb7
        data_need_to_be_written = 0x0018 |( efuse_addr<<6)
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
        
        #读取 0xbc为efuse_data_out_lo[15:0],efuse输出data的高16bit
        reg_addr = 0xbc
        value1 = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbc = 0x{value1:02X}")
        
        #读取 0xbd为efuse_data_out_lo[15:0],efuse输出data的低16bit
        reg_addr = 0xbd
        value2 = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbd = 0x{value2:02X}")
            
        final_data = (value1|value2)
        
        #write addr=8'hb7 data=16'h0008    //关闭efuse
        reg_addr = 0xb7
        data_need_to_be_written = 0x0008           
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
         
        #writeaddr=8'hb7 data=16'h0000 //关闭时钟
        reg_addr = 0xb7
        data_need_to_be_written = 0x0000          
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
         
        #切换efuse时钟为32k 0xbf data[14]=1'b0
        reg_addr = 0xbf
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print(f"写入0xbf data[14]=0")  
         
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
        data_width = UI_DATA_WIDTH #I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        #在此处添加写入efuse的逻辑
         #判断0xbe是否为0
        reg_addr = 0xbe
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xbe = 0x{value:02X}")
        if (value&0xf) != 0:
            print(f"efuse idle不为0，读取失败")
            return 0

        #切换efuse时钟为osc 0xbf data[14]=1'b1
        reg_addr = 0xbf
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 14, 14)
        print(f"写入0xbf data[14]=1")  
        
        time.sleep(0.1/1000)
        
        #开启efuse clk en,read mode write addr=(10'hb7) Write data=16'h0009
        reg_addr = 0xb7
        data_need_to_be_written = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 0x0009")
        
        #打开function turn on write addr=(10'hb7)Write data=16'h 0019?
        reg_addr = 0xb7
        data_need_to_be_written = 0x0019
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 0x0019")
            
        gui_data_to_be_written = (UI_DATA_VAL<<16) + UI_DATA_VAL;
        for i in range(0,32):
            if  (((gui_data_to_be_written >> i) & 0x1) == 1):
                efuse_addr = UI_REG_ADDR + 16*i;  
                #写入单个efuse 
                #Write data= {bits[2:0],address[6:0],6'b01_1001})
                reg_addr = 0xb7
                data_need_to_be_written = (0x0019 |( efuse_addr<<6))
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
            
                #Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1001})   //单次write trigger
                reg_addr = 0xb7
                data_need_to_be_written = (0x0039 |( efuse_addr<<6))     
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                
                #Write data= {efuse_sel, bits[4:0],address[3:0],6'b01_1001}) //单次write trigger关闭
                reg_addr = 0xb7
                data_need_to_be_written = (0x0019 |( efuse_addr<<6))         
                i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
                print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                time.sleep(0.1/1000)
                           
        #write addr=8'hb7 data=16'h0009    //关闭efuse
        reg_addr = 0xb7
        data_need_to_be_written = 0x0009           
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")
                    
        #writeaddr=8'hb7 data=16'h0000 //关闭时钟
        reg_addr = 0xb7
        data_need_to_be_written = 0x0000          
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xb7 = 0x{data_need_to_be_written:04X}")

         #切换efuse时钟为32k 0xbf data[14]=1'b0
        reg_addr = 0xbf
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 14, 14)
        print(f"写入0xbf data[14]=0") 

        return True
        
    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
