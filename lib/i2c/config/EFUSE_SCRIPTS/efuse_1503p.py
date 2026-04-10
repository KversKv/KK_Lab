# ------------------------------------------------------------------------------
# 在 I2C Tool 中执行 eFuse 脚本
# ------------------------------------------------------------------------------
import logging
_logger = logging.getLogger(__name__)

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
#i2c_interface.read(i2c_speed, ui_dev_addr, ui_reg_addr, data_width) #读取寄存器  
#i2c_interface.write(i2c_speed, ui_dev_addr, ui_reg_addr, ui_data_val, data_width) #写入寄存器
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
    # value = i2c_interface.read(i2c_speed, ui_dev_addr, reg_offset, data_width)
    
    # print(f"从eFuse地址/偏移量 0x{reg_offset:02X} 读取到值: 0x{value:02X}")
    # return value
#---------------------------------------------------------------------------------------#
    
    try:
        # i2c_speed = I2CSpeedMode.SPEED_100K
        # ui_data_width = I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        # reg_158_addr = 0x158
        # reg_158_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_158_addr, ui_data_width)
        # print(f"读取0x158 = 0x{reg_158_data:02X}")
        # if reg_158_data != 0:
        #     return False
        
        # reg_159_addr = 0x159
        # reg_159_data = 0x4000
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_159_addr, reg_159_data, ui_data_width)
        # print(f"写入0x159 = 0x{reg_159_data:02X}")

        # #开启efuse clk en,read mode write addr=(10'hb7) Write data=16'h0008
        # reg_b7_addr = 0xb7
        # reg_b7_data = 0x0008
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        # print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        # #打开function turn on write addr=(10'hb7)Write data=16'h 0018?
        # reg_b7_addr = 0xb7
        # reg_b7_data = 0x0018
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        # print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        # #读取单个efuse
        # #写入address[3:0]仅address4位和efuse_sel有效 write addr=(10'hb7) Write data= {bits[2:0],address[6:0],6'b01_1000})
        # efuse_data_list = []
        # for i in range(4):
        #     time.sleep(0.1)
        #     efuse_addr = reg_offset*4+i
        #     reg_b7_addr = 0xb7
        #     reg_b7_data = (0x0018 |( efuse_addr<<6))
        #     i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        #     print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        #     #单次read trigger write addr=(8'hb7) Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1000})
        #     reg_b7_addr = 0xb7
        #     reg_b7_data = (0x0038 |( efuse_addr<<6))
        #     i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        #     print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        #     #单次read trigger关闭 write addr=(8'hb7) Write data= {efuse_sel,bits[4:0],address[3:0],6'b01_1000})
        #     reg_b7_addr = 0xb7
        #     reg_b7_data = (0x0018 |( efuse_addr<<6))
        #     i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        #     print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        #     time.sleep(0.02)

        #     #读取 0xbe为efuse_data_out_lo[15:0],efuse输出data的低16bit
        #     reg_be_addr = 0xbe
        #     reg_be_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_be_addr, ui_data_width)
        #     print(f"读取0xbe = 0x{reg_be_data:02X}")
        #     efuse_data_list.append(reg_be_data)

        # # 提取原始的高 8 位 (现在位于 Python 值的低 8 位)
        # H0 = efuse_data_list[0] & 0xFF
        # H1 = efuse_data_list[1] & 0xFF
        # H2 = efuse_data_list[2] & 0xFF
        # H3 = efuse_data_list[3] & 0xFF
        # # 构建 PartA = H1 H0
        # PartA = (H1 << 8) | H0
        # # 构建 PartB = H3 H2
        # PartB = (H3 << 8) | H2
        # # 进行最终的按位或
        # efuse_data = PartA | PartB
        # # 打印结果，建议用 04X 格式化以便看清 16 位
        # print(f"计算后的 efuse_data = 0x{efuse_data:04X}")

        # #关闭efuse
        # reg_b7_addr = 0xb7
        # reg_b7_data = 0x0008
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        # print(f"写入0xb7 = 0x{reg_b7_data:02X}")
        
        # #关闭时钟
        # reg_b7_addr = 0xb7
        # reg_b7_data = 0x0000
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        # print(f"写入0xb7 = 0x{reg_b7_data:02X}")

        # #切换efuse时钟为32k write addr=(10'h159)Write data=16'h0000
        # reg_159_addr = 0x159
        # reg_159_data = 0x0000
        # i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_159_addr, reg_159_data, ui_data_width)
        # print(f"写入0x159 = 0x{reg_159_data:02X}")

        i2c_speed = I2CSpeedMode.SPEED_100K
        ui_data_width = I2CWidthFlag.BIT_8 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit
        efuse_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, UI_REG_ADDR, ui_data_width)
        _logger.info("读取位宽：%s", UI_DATA_WIDTH)
        _logger.info("读取0x%02X = 0x%02X", UI_REG_ADDR, efuse_data)
        return efuse_data
        
    except I2CError as e:
        _logger.error("I2C通信错误: %s", e)
        return -1
    except Exception as e:
        _logger.error("意外错误: %s - %s", type(e).__name__, e)
        return -1
    


def write_efuse(reg_offset: int, data: int) -> bool:
    """
    Args:
        reg_offset (int): 要写入的eFuse内部地址/偏移量
        data (int): 要写入的数据
        high_bit (int, 可选): 位操作的高位 (默认-1, 表示不按位写)
        low_bit (int, 可选): 位操作的低位 (默认-1, 表示不按位写)
    
    Raises:
        I2CError: 如果I2C通信失败
        Exception: 其他意外错误
    """

    try:
        i2c_speed = I2CSpeedMode.SPEED_100K
        ui_data_width = I2CWidthFlag.BIT_10 # BIT_8 : 8bit, BIT_10 : 16bit, BIT_32 : 32bit

        reg_158_addr = 0x158
        reg_158_data = i2c_interface.read(i2c_speed, UI_DEV_ADDR, reg_158_addr, ui_data_width)
        _logger.info("读取0x158 = 0x%02X", reg_158_data)
        if reg_158_data != 0:
            return False
        
        reg_159_addr = 0x159
        reg_159_data = 0x4000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_159_addr, reg_159_data, ui_data_width)

        #升启efuse clk en,read mode write addr=(10'hb7) Write data=16'h0009
        reg_b7_addr = 0xb7
        reg_b7_data = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

        #打开function turn on write addr=(10'hb7)Write data=16'h 0019?
        reg_b7_addr = 0xb7
        reg_b7_data = 0x0019
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

        group_page_size = 32 / 8
        first_in_group = reg_offset * group_page_size
        low_8 = data & 0x00ff
        high_8 = data & 0xff00
        for i in range(16):
            if (low_8 >> i) & 0x1:
                efuse_addr = (i << 7) | first_in_group
            elif (high_8 >> i) & 0x1:
                efuse_addr = ((i - 8) << 7) | (first_in_group + 1)
            else:
                continue

            #写入单个efuse 
            reg_b7_addr = 0xb7
            reg_b7_data = (0x0019 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

            #Write data= {efuse_sel,bits[4:0],address[3:0],6'b11_1001})   //单次write trigger
            reg_b7_addr = 0xb7
            reg_b7_data = (0x0039 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

            reg_b7_addr = 0xb7
            reg_b7_data = (0x0019 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

            #Write data= {efuse_sel, bits[4:0],address[3:0],6'b01_1001}) //单次write trigger关闭
            efuse_addr = efuse_addr + 2
            reg_b7_addr = 0xb7
            reg_b7_data = (0x0019 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

            #Write data= {bits[2:0],address[6:0],6'b01_1001})
            reg_b7_addr = 0xb7
            reg_b7_data = (0x0039 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)
            
            #Write data= {efuse_sel, bits[4:0],address[3:0],6'b11_1001})   //单次write trigger
            reg_b7_addr = 0xb7
            reg_b7_data = (0x0019 |( efuse_addr<<6))
            i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
            _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

        #关闭efuse
        reg_b7_addr = 0xb7
        reg_b7_data = 0x0009
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

        #
        reg_b7_addr = 0xb7
        reg_b7_data = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_b7_addr, reg_b7_data, ui_data_width)
        _logger.debug("写入0xb7 = 0x%02X", reg_b7_data)

        #切换efuse时钟为32k write addr=(10'h159)Write data=16'h0000
        reg_159_addr = 0x159
        reg_159_data = 0x0000
        i2c_interface.write(i2c_speed, UI_DEV_ADDR, reg_159_addr, reg_159_data, ui_data_width)
        _logger.debug("写入0x159 = 0x%02X", reg_159_data)

        return True
        
    except I2CError as e:
        _logger.error("I2C通信错误: %s", e)
        return False
    except Exception as e:
        _logger.error("意外错误: %s - %s", type(e).__name__, e)
        return False