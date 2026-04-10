#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I2C读写接口简单调用Demo

直接使用I2C接口进行读写操作的简单示例
包含8位、10位、32位地址/数据宽度的基本用法

作者: 芯片调试工具
创建时间: 2025
"""

import sys
import time
from pathlib import Path


script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# 导入I2C接口
from Bes_I2CIO_Interface import BESI2CIO, I2CSpeedMode, I2CWidthFlag

# 导入EFuse脚本调用器
from efuse_script_caller import EFuseScriptCaller

import logging
logger = logging.getLogger(__name__)

def main():
    """主函数 - 直接演示I2C读写操作"""
    logger.info("I2C接口简单调用Demo")
    logger.info("=" * 50)
    
    dll_path = str(script_dir / "config" / "BES_USBIO_I2C_X64.dll")
    try:
        i2c = BESI2CIO(dll_path)
        logger.info("I2C接口初始化成功")
    except Exception as e:
        logger.error("I2C接口初始化失败: %s", e)
        return 1
    
    # 基本参数
    device_addr = 0x27  # I2C设备地址
    speed_mode = I2CSpeedMode.SPEED_100K  # 100kHz通信速度
    
    logger.info("=" * 50)
    logger.info("I2C读写演示 (8位模式)")
    logger.info("=" * 50)

#****************************************************************#
#*****************************I2C读写操作*****************************#
#****************************************************************#

    # 示例参数 (8位模式)
    reg_addr = 0x02              # 寄存器地址
    test_data = 0x2445           # 测试数据
    width_flag = I2CWidthFlag.BIT_10  # 位宽标志
    
    # 其他位宽模式只需修改以下参数:
    # 10位模式: reg_addr=0x0200, width_flag=I2CWidthFlag.BIT_10
    # 32位模式: reg_addr=0x10000020, test_data=0x12345678, width_flag=I2CWidthFlag.BIT_32
    
    try:
        logger.info("写入: 设备0x%02X, 寄存器0x%02X, 数据0x%04X", device_addr, reg_addr, test_data)

        # I2C读取
        read_data = i2c.read(
            speed_mode,           # 速度模式
            device_addr,          # 设备地址
            reg_addr,             # 寄存器地址  
            width_flag            # 位宽标志
        )
        logger.info("读取: 0x%04X", read_data)

        reg_addr = 0x02
        
        # I2C写入 (已注释，如需测试请取消注释)
        # i2c.write(
        #     speed_mode,           # 速度模式
        #     device_addr,          # 设备地址  
        #     reg_addr,             # 寄存器地址
        #     test_data,            # 写入数据
        #     width_flag            # 位宽标志
        # )
        # print("写入成功")
        
        time.sleep(0.1)  # 延迟确保写入完成

        reg_addr = 0x02

        # I2C读取
        read_data = i2c.read(
            speed_mode,           # 速度模式
            device_addr,          # 设备地址
            reg_addr,             # 寄存器地址  
            width_flag            # 位宽标志
        )
        logger.info("读取: 0x%04X", read_data)
        
    except Exception as e:
        logger.error("I2C操作失败: %s", e)
    
#****************************************************************#
#*****************************按位操作*****************************#
#****************************************************************#

    logger.info("=" * 50)
    logger.info("位操作演示")
    logger.info("=" * 50)
    
    # 位操作：直接使用I2C接口的按位写功能
    # reg_addr_bit = 0x20
    
    # try:
        
    #     # 按位写：修改位[7:4]为0xA（直接使用I2C接口的按位写功能）
    #     bit_value = 0xA
    #     high_bit = 7
    #     low_bit = 4
        
    #     print(f"按位写: 设置位[{high_bit}:{low_bit}] = 0x{bit_value:X}")
    #     i2c.write(
    #         speed_mode,           # 速度模式
    #         device_addr,          # 设备地址
    #         reg_addr_bit,         # 寄存器地址
    #         bit_value,            # 要写入的位值
    #         I2CWidthFlag.BIT_8,   # 位宽标志
    #         high_bit,             # 高位位置
    #         low_bit               # 低位位置
    #     )
        
    #     time.sleep(0.1)
        
    #     # 读取按位写结果
    #     final_value = i2c.read(speed_mode, device_addr, reg_addr_bit, I2CWidthFlag.BIT_8)
    #     print(f"按位写结果: 0x{final_value:04X}")
            
    # except Exception as e:
    #     print(f"位操作失败: {e}")
    
#****************************************************************#
#*****************************EFuse脚本调用*****************************#
#****************************************************************#

    logger.info("=" * 50)
    logger.info("EFuse脚本调用演示")
    logger.info("=" * 50)
    
    efuse_device_addr = 0x27
    efuse_reg_addr = 0x02
    efuse_data_width = I2CWidthFlag.BIT_8
    
    try:
        efuse_caller = EFuseScriptCaller(i2c)
        
        logger.info("读取eFuse参数:")
        logger.info("  设备地址: 0x%02X", efuse_device_addr)
        logger.info("  寄存器地址: 0x%02X", efuse_reg_addr)
        logger.info("  数据宽度: %s", efuse_data_width.name)
        
        success, efuse_data = efuse_caller.read_efuse(
            efuse_device_addr,          # 设备地址
            efuse_reg_addr,             # 寄存器地址  
            efuse_data_width,           # 数据宽度
            speed_mode,                 # 速度模式
            "efuse_1503p.py",           # 脚本文件名
            "1503p"                     # 芯片名称
        )
        
        if success:
            logger.info("eFuse读取成功: 寄存器0x%02X = 0x%04X", efuse_reg_addr, efuse_data)
        else:
            logger.warning("eFuse读取失败: 寄存器0x%02X", efuse_reg_addr)
        
        logger.info("-" * 30)
        
    #     # 写入演示（已注释）
    #     write_data = 0x1234
    #     print(f"写入eFuse参数:")
    #     print(f"  设备地址: 0x{efuse_device_addr:02X}")
    #     print(f"  寄存器地址: 0x{efuse_reg_addr:02X}")
    #     print(f"  写入数据: 0x{write_data:04X}")
    #     print(f"  数据宽度: {efuse_data_width.name}")
    #     print("\n  警告: eFuse写入是不可逆的操作！")
        
    #     # 取消注释以下行来执行实际的eFuse写入
    #     # write_success = efuse_caller.write_efuse(
    #     #     efuse_device_addr,          # 设备地址
    #     #     efuse_reg_addr,             # 寄存器地址
    #     #     write_data,                 # 写入数据
    #     #     efuse_data_width            # 数据宽度
    #     #     speed_mode,                 # 速度模式
    #     #     "efuse_1503p.py",           # 脚本文件名
    #     #     "1503p"                     # 芯片名称
    #     # )
    #     # if write_success:
    #     #     print(f" eFuse写入成功: 寄存器0x{efuse_reg_addr:02X}")
    #     # else:
    #     #     print(f" eFuse写入失败: 寄存器0x{efuse_reg_addr:02X}")
        
    #     print("（写入操作已注释，如需测试请取消注释）")
        
    except Exception as e:
        logger.error("EFuse脚本调用失败: %s", e)


def i2c_test():
    """I2C测试函数 - 演示10bit模式下的读写操作"""
    logger.info("=" * 50)
    logger.info("I2C测试函数 (10bit模式)")
    logger.info("=" * 50)
    
    script_dir = Path(__file__).parent
    dll_path = str(script_dir / "config" / "BES_USBIO_I2C_X64.dll")
    
    try:
        i2c = BESI2CIO(dll_path)
        logger.info("I2C接口初始化成功")
    except Exception as e:
        logger.error("I2C接口初始化失败: %s", e)
        return False
    
    device_addr = 0x17
    speed_mode = I2CSpeedMode.SPEED_100K
    width_flag = I2CWidthFlag.BIT_10
    
    try:
        reg_addr_read = 0x0000
        logger.info("1. 读取操作：")
        logger.info("   设备地址: 0x%02X", device_addr)
        logger.info("   寄存器地址: 0x%04X", reg_addr_read)
        logger.info("   位宽模式: %s", width_flag.name)
        
        read_data = i2c.read(
            speed_mode,
            device_addr,
            reg_addr_read,
            width_flag
        )
        logger.info("   读取结果: 0x%04X", read_data)
        
        reg_addr_write = 0x1e7
        write_data = 0x20AA
        logger.info("2. 写入操作：")
        logger.info("   设备地址: 0x%02X", device_addr)
        logger.info("   寄存器地址: 0x%04X", reg_addr_write)
        logger.info("   写入数据: 0x%04X", write_data)
        logger.info("   位宽模式: %s", width_flag.name)
        
        i2c.write(
            speed_mode,
            device_addr,
            reg_addr_write,
            write_data,
            width_flag
        )
        logger.info("   写入成功")
        
        time.sleep(0.1)
        logger.info("3. 验证写入结果：")
        verify_data = i2c.read(
            speed_mode,
            device_addr,
            reg_addr_write,
            width_flag
        )
        logger.info("   寄存器地址0x%04X的当前值: 0x%04X", reg_addr_write, verify_data)
        logger.info("   验证%s", '成功' if verify_data == write_data else '失败')
        
        return True
        
    except Exception as e:
        logger.error("I2C测试操作失败: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    main()
    
    logger.info("=" * 50)
    logger.info("运行新增的I2C测试函数")
    logger.info("=" * 50)
    i2c_test()