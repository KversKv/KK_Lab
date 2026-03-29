import abc
import ctypes
import enum
import threading
import os
import sys
from typing import Optional, Tuple, TypeVar, Generic, Union, ClassVar, List


# 定义I2C速度模式枚举
class I2CSpeedMode(enum.IntEnum):
    """I2C通信速度模式枚举。"""
    SPEED_20K = 0  # 20kHz
    SPEED_100K = 1  # 100kHz（标准模式）
    SPEED_400K = 2  # 400kHz（快速模式）
    SPEED_750K = 3  # 750kHz

# 定义位宽标志枚举
class I2CWidthFlag(enum.IntEnum):
    """I2C地址和数据宽度标志枚举。"""
    BIT_8 = 0   # 8位寄存器地址，16位数据
    BIT_10 = 1  # 10位寄存器地址（实际使用16位），16位数据
    BIT_32 = 2  # 32位寄存器地址，32位数据

# 定义I2C操作状态枚举
class I2CStatus(enum.IntEnum):
    """I2C操作状态码枚举。"""
    SUCCESS = 0
    ERROR_OPEN_DEVICE = -1
    ERROR_SET_STREAM = -2
    ERROR_STREAM_I2C = -3
    ERROR_WRITE_DATA = -4
    ERROR_INVALID_FLAG = -5
    ERROR_BUFFER_PREP = -6
    ERROR_PYTHON_EXCEPTION = -100  # 用于Python特有异常

# 自定义异常类
class I2CError(Exception):
    """I2C操作异常基类。"""
    def __init__(self, status: I2CStatus, message: str = ""):
        self.status = status
        self.message = message
        super().__init__(f"I2C Error: {status.name} ({status.value}). {message}")

class I2CDeviceError(I2CError):
    """设备相关错误。"""
    pass

class I2COperationError(I2CError):
    """操作相关错误。"""
    pass

class I2CParameterError(I2CError):
    """参数相关错误。"""
    pass

# 定义抽象I2C接口
class II2CIO(abc.ABC):
    """
    I2C读写操作的抽象接口。
    
    该接口定义了I2C设备读写寄存器的标准操作集，遵循单一职责原则。
    实现类需要提供具体的I2C通信实现方法。
    
    所有方法都应该是线程安全的，适合在多线程环境中使用。
    """
    
    @abc.abstractmethod
    def read(self, 
             speed_mode: I2CSpeedMode, 
             device_address: int, 
             register_address: int, 
             width_flag: I2CWidthFlag) -> int:
        """
        从I2C设备读取数据。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            width_flag: 地址和数据宽度标志
            
        Returns:
            读取的数据值
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        pass
    
    @abc.abstractmethod
    def write(self, 
              speed_mode: I2CSpeedMode, 
              device_address: int, 
              register_address: int, 
              write_data: int, 
              width_flag: I2CWidthFlag, 
              high_bit: int = -1, 
              low_bit: int = -1) -> None:
        """
        向I2C设备写入数据。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            write_data: 要写入的数据
            width_flag: 地址和数据宽度标志
            high_bit: 位操作的高位位置，-1表示不使用按位写
            low_bit: 位操作的低位位置，-1表示不使用按位写
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        pass
    
    @abc.abstractmethod
    def read_data(self, 
                  speed_mode: I2CSpeedMode, 
                  device_address: int, 
                  register_address: int, 
                  width_flag: I2CWidthFlag) -> int:
        """
        使用手动命令流从I2C设备读取数据。
        
        此方法使用底层命令流手动构造I2C通信，提供更灵活的控制。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            width_flag: 地址和数据宽度标志
            
        Returns:
            读取的数据值
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        pass
    
    @abc.abstractmethod
    def write_data(self, 
                   speed_mode: I2CSpeedMode, 
                   device_address: int, 
                   register_address: int, 
                   write_data: int, 
                   width_flag: I2CWidthFlag, 
                   high_bit: int = -1, 
                   low_bit: int = -1) -> None:
        """
        使用手动命令流向I2C设备写入数据。
        
        此方法使用底层命令流手动构造I2C通信，提供更灵活的控制。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            write_data: 要写入的数据
            width_flag: 地址和数据宽度标志
            high_bit: 位操作的高位位置，-1表示不使用按位写
            low_bit: 位操作的低位位置，-1表示不使用按位写
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        pass


class BESI2CIO(II2CIO):
    """
    基于CH341芯片的I2C读写操作具体实现。
    
    该类封装了C++动态库中的I2C操作函数，提供了线程安全的接口实现。
    """
    
    # 类变量，用于线程安全
    _lock: ClassVar[threading.RLock] = threading.RLock()
    
    # DLL文件名列表，按优先级排序
    _DLL_NAMES: ClassVar[List[str]] = [
        "BES_USBIO_I2C_X64.dll",  # 64位版本
        "BES_USBIO_I2C.dll",     # 32位版本
    ]
    
    @classmethod
    def _find_dll(cls) -> Optional[str]:
        """
        在当前脚本所在目录下查找DLL文件。
        
        Returns:
            找到的DLL文件的完整路径，如果未找到则返回None
        """
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 遍历DLL名称列表
        for dll_name in cls._DLL_NAMES:
            dll_path = os.path.join(script_dir, dll_name)
            if os.path.isfile(dll_path):
                return dll_path
        
        return None
    
    def __init__(self, dll_path: Optional[str] = None):
        """
        初始化I2C接口。
        
        Args:
            dll_path: 动态库路径，如果为None，则在当前脚本所在目录下查找
            
        Raises:
            OSError: 加载动态库失败时
        """
        try:
            # 优先使用传入的DLL路径
            if dll_path is None:
                # 如果没有指定，才尝试自动查找
                dll_path = self._find_dll()
                if dll_path is None:
                    # 如果未找到，抛出异常
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    dll_names_str = ", ".join(self._DLL_NAMES)
                    raise OSError(f"在目录 {script_dir} 下未找到动态库文件：{dll_names_str}")
            
            # 加载DLL
            self._dll = ctypes.CDLL(dll_path)
            
            # 配置函数原型
            self._configure_function_prototypes()
            
        except OSError as e:
            raise OSError(f"无法加载动态库: {e}")
    
    def _configure_function_prototypes(self) -> None:
        """配置DLL函数的参数和返回类型。"""
        # BES_I2C_IO_Read
        self._dll.BES_I2C_IO_Read.argtypes = [
            ctypes.c_uint,  # i2c_speed_mode
            ctypes.c_uint,  # dev_addr
            ctypes.c_uint,  # reg_addr
            ctypes.POINTER(ctypes.c_uint),  # read_data
            ctypes.c_int    # bit_flag
        ]
        self._dll.BES_I2C_IO_Read.restype = ctypes.c_int
        
        # BES_I2C_IO_Write
        self._dll.BES_I2C_IO_Write.argtypes = [
            ctypes.c_uint,  # i2c_speed_mode
            ctypes.c_uint,  # dev_addr
            ctypes.c_uint,  # reg_addr
            ctypes.c_uint,  # write_data
            ctypes.c_int,   # bit_flag
            ctypes.c_int,   # h_bit
            ctypes.c_int    # l_bit
        ]
        self._dll.BES_I2C_IO_Write.restype = ctypes.c_int
        
        # BES_I2C_IO_ReadData
        self._dll.BES_I2C_IO_ReadData.argtypes = [
            ctypes.c_uint,  # i2c_speed_mode
            ctypes.c_uint,  # dev_addr
            ctypes.c_uint,  # reg_addr
            ctypes.POINTER(ctypes.c_uint),  # read_data
            ctypes.c_int    # bit_flag
        ]
        self._dll.BES_I2C_IO_ReadData.restype = ctypes.c_int
        
        # BES_I2C_IO_WriteData
        self._dll.BES_I2C_IO_WriteData.argtypes = [
            ctypes.c_uint,  # i2c_speed_mode
            ctypes.c_uint,  # dev_addr
            ctypes.c_uint,  # reg_addr
            ctypes.c_uint,  # write_data
            ctypes.c_int,   # bit_flag
            ctypes.c_int,   # h_bit
            ctypes.c_int    # l_bit
        ]
        self._dll.BES_I2C_IO_WriteData.restype = ctypes.c_int
    
    def _handle_status(self, status: int) -> None:
        """
        处理I2C操作状态码，根据状态码抛出相应异常。
        
        Args:
            status: I2C操作状态码
            
        Raises:
            I2CDeviceError: 设备相关错误
            I2COperationError: 操作相关错误
            I2CParameterError: 参数相关错误
        """
        if status == I2CStatus.SUCCESS:
            return
        
        # 将整数状态转换为枚举
        try:
            status_enum = I2CStatus(status)
        except ValueError:
            status_enum = I2CStatus.ERROR_PYTHON_EXCEPTION
        
        # 根据状态类型抛出对应异常
        if status_enum in (I2CStatus.ERROR_OPEN_DEVICE, I2CStatus.ERROR_SET_STREAM):
            raise I2CDeviceError(status_enum)
        elif status_enum in (I2CStatus.ERROR_STREAM_I2C, I2CStatus.ERROR_WRITE_DATA, I2CStatus.ERROR_BUFFER_PREP):
            raise I2COperationError(status_enum)
        elif status_enum == I2CStatus.ERROR_INVALID_FLAG:
            raise I2CParameterError(status_enum)
        else:
            raise I2CError(status_enum)
    
    def read(self, 
             speed_mode: I2CSpeedMode, 
             device_address: int, 
             register_address: int, 
             width_flag: I2CWidthFlag) -> int:
        """
        从I2C设备读取数据。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            width_flag: 地址和数据宽度标志
            
        Returns:
            读取的数据值
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        read_data = ctypes.c_uint(0)
        
        with self._lock:
            status = self._dll.BES_I2C_IO_Read(
                ctypes.c_uint(speed_mode),
                ctypes.c_uint(device_address),
                ctypes.c_uint(register_address),
                ctypes.byref(read_data),
                ctypes.c_int(width_flag)
            )
            self._handle_status(status)
        
        return read_data.value
    
    def write(self, 
              speed_mode: I2CSpeedMode, 
              device_address: int, 
              register_address: int, 
              write_data: int, 
              width_flag: I2CWidthFlag, 
              high_bit: int = -1, 
              low_bit: int = -1) -> None:
        """
        向I2C设备写入数据。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            write_data: 要写入的数据
            width_flag: 地址和数据宽度标志
            high_bit: 位操作的高位位置，-1表示不使用按位写
            low_bit: 位操作的低位位置，-1表示不使用按位写
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        with self._lock:
            status = self._dll.BES_I2C_IO_Write(
                ctypes.c_uint(speed_mode),
                ctypes.c_uint(device_address),
                ctypes.c_uint(register_address),
                ctypes.c_uint(write_data),
                ctypes.c_int(width_flag),
                ctypes.c_int(high_bit),
                ctypes.c_int(low_bit)
            )
            self._handle_status(status)
    
    def read_data(self, 
                  speed_mode: I2CSpeedMode, 
                  device_address: int, 
                  register_address: int, 
                  width_flag: I2CWidthFlag) -> int:
        """
        使用手动命令流从I2C设备读取数据。
        
        此方法使用底层命令流手动构造I2C通信，提供更灵活的控制。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            width_flag: 地址和数据宽度标志
            
        Returns:
            读取的数据值
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        read_data = ctypes.c_uint(0)
        
        with self._lock:
            status = self._dll.BES_I2C_IO_ReadData(
                ctypes.c_uint(speed_mode),
                ctypes.c_uint(device_address),
                ctypes.c_uint(register_address),
                ctypes.byref(read_data),
                ctypes.c_int(width_flag)
            )
            self._handle_status(status)
        
        return read_data.value
    
    def write_data(self, 
                   speed_mode: I2CSpeedMode, 
                   device_address: int, 
                   register_address: int, 
                   write_data: int, 
                   width_flag: I2CWidthFlag, 
                   high_bit: int = -1, 
                   low_bit: int = -1) -> None:
        """
        使用手动命令流向I2C设备写入数据。
        
        此方法使用底层命令流手动构造I2C通信，提供更灵活的控制。
        
        Args:
            speed_mode: I2C通信速度模式
            device_address: I2C设备地址(7位)
            register_address: 寄存器地址
            write_data: 要写入的数据
            width_flag: 地址和数据宽度标志
            high_bit: 位操作的高位位置，-1表示不使用按位写
            low_bit: 位操作的低位位置，-1表示不使用按位写
            
        Raises:
            I2CDeviceError: 设备打开或设置失败时
            I2COperationError: I2C通信操作失败时
            I2CParameterError: 参数无效时
        """
        with self._lock:
            status = self._dll.BES_I2C_IO_WriteData(
                ctypes.c_uint(speed_mode),
                ctypes.c_uint(device_address),
                ctypes.c_uint(register_address),
                ctypes.c_uint(write_data),
                ctypes.c_int(width_flag),
                ctypes.c_int(high_bit),
                ctypes.c_int(low_bit)
            )
            self._handle_status(status)


# 示例用法
if __name__ == "__main__":
    try:
        #创建当前脚本所在目录
        from utils.g_vars import HOME_DIR
        script_dir = str(HOME_DIR / "config" / "i2c_dll" / "BES_USBIO_I2C_X64.dll")
        # 创建I2C接口对象，不指定DLL路径，自动在脚本所在目录下查找
        i2c = BESI2CIO(script_dir)
        
        # 读取示例
        device_addr = 0x50  # 设备地址
        reg_addr = 0x00     # 寄存器地址
        
        # 使用标准I2C读取函数读取数据
        data = i2c.read(
            I2CSpeedMode.SPEED_100K,  # 使用100kHz速度模式
            device_addr,
            reg_addr,
            I2CWidthFlag.BIT_8       # 使用8位寄存器地址、16位数据
        )
        print(f"读取数据: 0x{data:04X}")
        
        # 写入示例
        i2c.write(
            I2CSpeedMode.SPEED_100K,  # 使用100kHz速度模式
            device_addr,
            reg_addr,
            0x1234,                  # 写入数据
            I2CWidthFlag.BIT_8       # 使用8位寄存器地址、16位数据
        )
        print("数据写入成功")
        
    except I2CDeviceError as e:
        print(f"设备错误: {e}")
    except I2COperationError as e:
        print(f"操作错误: {e}")
    except I2CParameterError as e:
        print(f"参数错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
