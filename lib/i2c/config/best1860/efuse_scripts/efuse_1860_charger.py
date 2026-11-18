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
        #判断0xaa是否为0
        reg_addr = 0xaa
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xaa = 0x{value:02X}")
        value = (value & 0x1E00)
        if value != 0:
            print(f"efuse idle不为0，读取失败")
            return 0

        #打开32K reg_pu_lpo=1,reg_pu_lpo_dr=1
        reg_addr = 0x23
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x3, data_width, 6, 5)
        print(f"写入0x23 data[6:5]=0x3")
        #打开bg_en reg_bg_core_en=1,reg_bg_core_en_dr=1
        reg_addr = 0x2
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x3, data_width, 1, 0)
        print(f"写入0x2 data[1:0]=0x3")
        
        #切换efuse时钟为osc 0x40 data[11]=1'h0
        reg_addr = 0x40
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 11, 11)
        print(f"写入0x40 data[11]=0")
        
        #读操作
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 0, 0)
        print(f"写入0xa0 data[0]=0") 
        #开启efuse clk en     
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 1, 1)
        print(f"写入0xa0 data[1]=1") 
        #打开function turn on
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 2, 2)
        print(f"写入0xa0 data[2]=1")  
        time.sleep(0.1/1000)
                
        valuelist = []
        for i in range(0,2):
            time.sleep(0.1/1000)
            efuse_addr = UI_REG_ADDR*2+i
            reg_addr = 0xa1
            data_need_to_be_written = efuse_addr
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
            print(f"写入0xa1 = 0x{data_need_to_be_written:04X}")
                        
            #单次read trigger write addr=(8'h1a8) Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1000})
            reg_addr = 0xa0
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 3, 3)
            print(f"写入0xa0 data[3]=1")  
            #单次read trigger关闭 write addr=(8'h1a8) Write data= {efuse_sel,bits[4:0],address[3:0],6'b01_1000})
            reg_addr = 0xa0
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 3, 3)
            print(f"写入0xa0 data[3]=0")  

            time.sleep(0.02/1000)
            
            #读取 0xbe为efuse_data_out_lo[15:0],efuse输出data的低16bit
            reg_addr = 0xaa
            value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
            print(f"读取0xaa = 0x{value:02X}")
            valuelist.append((value&0x1fe)>>1)
         
        final_data =(((valuelist[1]<<8) & 0xff00)+(valuelist[0]&0xff))
        
        #清空地址
        reg_addr = 0xa1
        data_need_to_be_written = 0x0000          
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xa1 0")  
                    
        #读操作
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 0, 0)
        print(f"写入0xa0 data[0]=0") 
        #efuse clk en       
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 1, 1)
        print(f"写入0xa0 data[1]=0") 
        #function turn on
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 2, 2)
        print(f"写入0xa0 data[2]=0")    
         
        #关闭32K reg_pu_lpo=0,reg_pu_lpo_dr=0
        reg_addr = 0x23
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x0, data_width, 6, 5)
        print(f"写入0x23 data[6:5]=0x0")
        #关闭bg_en reg_bg_core_en=0,reg_bg_core_en_dr=0
        reg_addr = 0x2
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x0, data_width, 1, 0)
        print(f"写入0x2 data[1:0]=0x0")
        
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
        #判断0xaa是否为0
        reg_addr = 0xaa
        value = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_addr, data_width)
        print(f"读取0xaa = 0x{value:02X}")
        value = (value & 0x1E00)
        if value != 0:
            print(f"efuse idle不为0，读取失败")
            return 0
            
        #打开32K reg_pu_lpo=1,reg_pu_lpo_dr=1
        reg_addr = 0x23
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x3, data_width, 6, 5)
        print(f"写入0x23 data[6:5]=0x3")
        #打开bg_en reg_bg_core_en=1,reg_bg_core_en_dr=1
        reg_addr = 0x2
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x3, data_width, 1, 0)
        print(f"写入0x2 data[1:0]=0x3")
        
        #切换efuse时钟为osc 0x40 data[11]=1'h0
        reg_addr = 0x40
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 11, 11)
        print(f"写入0x40 data[11]=0")
        
        #reg_efuse_pgm_en_time
        reg_addr = 0xa5
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x78, data_width, 8, 0)
        print(f"写入0xa5 data[8:0]=0x78")
        
        #reg_efuse_addr_en_time
        reg_addr = 0xa5
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x1, data_width, 14, 9)
        print(f"写入0xa5 data[14:9]=0x1")
        
        #reg_efuse_strobe_pre_time
        reg_addr = 0xa6
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x5, data_width, 5, 0)
        print(f"写入0xa6 data[5:0]=0x5")
        
        #reg_efuse_pgm_strobe_time
        reg_addr = 0xa6
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x3B, data_width, 14, 6)
        print(f"写入0xa6 data[14:6]=0x3B")
        
        #reg_efuse_read_strobe_time
        reg_addr = 0xa7
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x12, data_width, 5, 0)
        print(f"写入0xa7 data[5:0]=0x12")
        
        #reg_efuse_pgm_cold_time
        reg_addr = 0xa7
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x96, data_width, 14, 6)
        print(f"写入0xa7 data[14:6]=0x96")
        
        #reg_efuse_read_cold_time
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x12, data_width, 5, 0)
        print(f"写入0xa8 data[5:0]=0x12")
        
        #reg_efuse_avdd_dis_time
        reg_addr = 0xa8
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0xC, data_width, 11, 6)
        print(f"写入0xa8 data[11:6]=0xC")
        
        time.sleep(0.05/1000)
        
        #写操作
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 0, 0)
        print(f"写入0xa0 data[0]=1") 
        #开启efuse clk en     
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 1, 1)
        print(f"写入0xa0 data[1]=1") 
        #打开function turn on
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 2, 2)
        print(f"写入0xa0 data[2]=1") 
        #clk_osc_sel
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 5, 5)
        print(f"写入0xa0 data[5]=1")      
        time.sleep(0.1/1000)

        for i in range(0,16):
            if ((UI_DATA_VAL >> i) & 0x1):
                if i<8:
                    efuse_addr = UI_REG_ADDR*2
                    efuse_bit = i
                else:
                    efuse_addr = UI_REG_ADDR*2+1
                    efuse_bit = i-8
            else:
                continue
            
            #写入单个efuse 
            #Write data= {bits[2:0],address[6:0],6'b01_1001})
            reg_addr = 0xa1;
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, efuse_addr, data_width,4,0)
            print(f"写入0xa1 data[4:0]=0x{efuse_addr:X}")
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, efuse_bit, data_width,7,5)
            print(f"写入0xa1 data[7:5]=0x{efuse_bit:X}")
            
            #单次read trigger write addr=(8'h1a8) Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1000})
            reg_addr = 0xa0
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 3, 3)
            print(f"写入0xa0 data[3]=1")  
            #单次read trigger关闭 write addr=(8'h1a8) Write data= {efuse_sel,bits[4:0],address[3:0],6'b01_1000})
            reg_addr = 0xa0
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 3, 3)
            print(f"写入0xa0 data[3]=0")  
            
        #清空地址
        reg_addr = 0xa1
        data_need_to_be_written = 0x0000          
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, data_need_to_be_written, data_width)
        print(f"写入0xa1 0")  
                    
        #读操作
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 0, 0)
        print(f"写入0xa0 data[0]=0") 
        #efuse clk en       
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 1, 1)
        print(f"写入0xa0 data[1]=0") 
        #function turn on
        reg_addr = 0xa0
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0, data_width, 2, 2)
        print(f"写入0xa0 data[2]=0")
        reg_addr = 0x40
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 1, data_width, 11, 11)
        print(f"写入0x40 data[11]=1") 
        #关闭32K reg_pu_lpo=0,reg_pu_lpo_dr=0
        reg_addr = 0x23
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x0, data_width, 6, 5)
        print(f"写入0x23 data[6:5]=0x0")
        #关闭bg_en reg_bg_core_en=0,reg_bg_core_en_dr=0
        reg_addr = 0x2
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_addr, 0x0, data_width, 1, 0)
        print(f"写入0x2 data[1:0]=0x0")        
        return True
        
    except I2CError as e:
        print(f"I2C通信错误: {e}")
        return False
    except Exception as e:
        print(f"意外错误: {type(e).__name__} - {e}")
        return False
