#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EFuse 脚本调用器

模拟主程序中的 eFuse 脚本调用机制，用于在独立的环境中调用 eFuse 脚本。
不依赖主程序的UI组件，通过参数传递必要的变量。

作者: 芯片调试工具
创建时间: 2025
"""

import sys
import importlib.util
import time
import traceback
from pathlib import Path
from typing import Optional, Tuple, Any

# 导入I2C接口
from Bes_I2CIO_Interface import BESI2CIO, I2CSpeedMode, I2CWidthFlag, I2CError

import logging
logger = logging.getLogger(__name__)


class EFuseScriptCaller:
    """EFuse脚本调用器类
    
    模拟主程序的eFuse脚本调用机制，支持动态加载脚本并注入必要的上下文变量。
    """
    
    def __init__(self, i2c_interface: BESI2CIO, efuse_scripts_dir: Optional[Path] = None):
        """
        初始化EFuse脚本调用器
        
        Args:
            i2c_interface: I2C接口实例
            efuse_scripts_dir: eFuse脚本目录路径，默认为当前目录下的config/EFUSE_SCRIPTS
        """
        self.i2c_interface = i2c_interface
        
        # 设置默认的eFuse脚本目录
        if efuse_scripts_dir is None:
            script_dir = Path(__file__).parent
            self.efuse_scripts_dir = script_dir / "config" / "EFUSE_SCRIPTS"
        else:
            self.efuse_scripts_dir = efuse_scripts_dir
            
        logger.info("EFuse脚本目录: %s", self.efuse_scripts_dir)
    
    def call_efuse_script_function(self, 
                                 script_filename: str,
                                 function_name: str,
                                 device_addr: int = 0x27,
                                 speed_mode: I2CSpeedMode = I2CSpeedMode.SPEED_100K,
                                 data_width: I2CWidthFlag = I2CWidthFlag.BIT_10,
                                 chip_name: str = "best1503p",
                                 *args) -> Tuple[bool, Any]:
        """
        调用eFuse脚本中的指定函数
        
        Args:
            script_filename: 脚本文件名
            function_name: 要调用的函数名
            device_addr: I2C设备地址
            speed_mode: I2C速度模式
            data_width: 数据宽度
            chip_name: 芯片名称
            *args: 传递给目标函数的参数
            
        Returns:
            (success, return_value) 元组
            - success: 调用是否成功
            - return_value: 函数返回值
        """
        # 构建脚本路径
        script_path = self.efuse_scripts_dir / script_filename
        
        log_prefix = f"EFuseScript({script_filename}->{function_name})"
        
        # 检查脚本文件是否存在
        if not script_path.exists() or not script_path.is_file():
            error_msg = f"脚本文件不存在: {script_path}"
            logger.error("%s: %s", log_prefix, error_msg)
            return False, None
        
        success_flag = False
        return_value = None
        
        try:
            # 创建唯一的模块名
            module_name_unique = f"efuse_module_{chip_name}_{Path(script_filename).stem}_{time.time_ns()}"
            
            # 使用importlib动态加载模块
            spec = importlib.util.spec_from_file_location(module_name_unique, str(script_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"无法为 {script_path} 创建模块规范")
            
            efuse_module = importlib.util.module_from_spec(spec)
            
            # 注入脚本需要的全局变量
            # 这些变量对应 efuse_1503p.py 中通过 globals().get() 获取的变量
            setattr(efuse_module, 'i2c_interface', self.i2c_interface)
            setattr(efuse_module, 'I2CSpeedMode', I2CSpeedMode)
            setattr(efuse_module, 'I2CWidthFlag', I2CWidthFlag)
            setattr(efuse_module, 'I2CError', I2CError)
            
            # 注入UI相关的变量（脚本通过globals().get()获取这些变量）
            setattr(efuse_module, 'ui_dev_addr', device_addr)  # 脚本会用这个赋值给UI_DEV_ADDR
            
            # 从args中提取寄存器地址和数据值
            reg_addr = args[0] if len(args) > 0 else 0  # 第一个参数是寄存器地址
            write_data = args[1] if len(args) > 1 else 0  # 第二个参数是写入数据（如果存在）
            
            setattr(efuse_module, 'ui_reg_addr', reg_addr)  # 使用传递的寄存器地址
            setattr(efuse_module, 'ui_data_hex', write_data)  # 使用传递的数据值
            setattr(efuse_module, 'ui_data_width', data_width)  # 使用传递的数据宽度
            setattr(efuse_module, 'ui_module_name_unique', f"{chip_name}_efuse")
            setattr(efuse_module, 'ui_chip_name', chip_name)
            
            # 将模块添加到sys.modules以支持相对导入
            sys.modules[module_name_unique] = efuse_module
            
            # 执行模块（运行顶层代码）
            spec.loader.exec_module(efuse_module)
            
            # 检查目标函数是否存在
            if hasattr(efuse_module, function_name):
                target_function = getattr(efuse_module, function_name)
                logger.info("%s: 正在调用函数 '%s'", log_prefix, function_name)
                
                return_value = target_function(*args)
                success_flag = True
                logger.info("%s: 函数 '%s' 执行完成，返回值: 0x%02X", log_prefix, function_name, return_value)
                
            else:
                error_msg = f"在脚本 '{script_filename}' 中未找到函数 '{function_name}'"
                logger.error("%s: %s", log_prefix, error_msg)
                
        except ImportError as e:
            error_msg = f"导入脚本模块失败: {e}"
            logger.error("%s: %s", log_prefix, error_msg)
            
        except I2CError as e:
            error_msg = f"I2C通信错误: {e}"
            logger.error("%s: %s", log_prefix, error_msg)
            
        except Exception as e:
            error_msg = f"脚本执行异常: {e}"
            logger.error("%s: %s", log_prefix, error_msg)
            logger.debug("--- 脚本执行异常详情 ---")
            logger.debug(traceback.format_exc())
            logger.debug("--- 异常结束 ---")
            
        finally:
            # 清理动态导入的模块
            if module_name_unique in sys.modules:
                del sys.modules[module_name_unique]
        
        return success_flag, return_value
    
    def read_efuse(self, device_addr: int, reg_addr: int, 
                   data_width: I2CWidthFlag, 
                   speed_mode: I2CSpeedMode = I2CSpeedMode.SPEED_100K, 
                   script_filename: str = "efuse_xxx.py", 
                   chip_name: str = "bestxxx") -> Tuple[bool, Any]:
        """
        调用eFuse读取函数
        
        Args:
            script_filename: 脚本文件名
            device_addr: I2C设备地址 (必须)
            reg_addr: eFuse寄存器地址 (必须)
            data_width: 数据宽度 (必须)
            speed_mode: I2C速度模式 (可选，默认100K)
            chip_name: 芯片名称 (可选)
            
        Returns:
            (success, data) 元组
        """
        success, return_value = self.call_efuse_script_function(
            script_filename, 'read_efuse', device_addr, speed_mode, data_width, 
            chip_name, reg_addr
        )
                
        return success, return_value
    
    def write_efuse(self, device_addr: int, reg_addr: int, 
                    write_data: int, data_width: I2CWidthFlag,
                    speed_mode: I2CSpeedMode = I2CSpeedMode.SPEED_100K,
                    script_filename: str = "efuse_xxx.py", 
                    chip_name: str = "bestxxx") -> bool:
        """
        调用eFuse写入函数
        
        Args:
            script_filename: 脚本文件名
            device_addr: I2C设备地址 (必须)
            reg_addr: eFuse寄存器地址 (必须)
            write_data: 要写入的数据 (必须)
            data_width: 数据宽度 (必须)
            speed_mode: I2C速度模式 (可选，默认100K)
            chip_name: 芯片名称 (可选)
            
        Returns:
            是否写入成功
        """
        success, return_value = self.call_efuse_script_function(
            script_filename, 'write_efuse', device_addr, speed_mode, data_width,
            chip_name, reg_addr, write_data
        )
                
        return success and return_value is True 