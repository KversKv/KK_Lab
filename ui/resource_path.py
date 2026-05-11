import sys
import os

APP_NAME = "KK_Lab"


def get_resource_base():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_user_data_dir(*subpaths: str) -> str:
    """
    返回**可写**的用户数据根目录 (或其子目录).

    设计原因 (面向 PyInstaller 分发):
      - onefile 模式下 sys._MEIPASS 是临时目录, 写入会在退出时丢失.
      - onedir 模式下 EXE 同目录可能位于 C:\\Program Files\\, 普通用户无写权限.
      - 因此运行时**所有可写数据**(配置/快捷指令/缓存) 一律落到用户目录.

    路径规则:
      - 已打包 (frozen): %APPDATA%\\KK_Lab\\<subpaths>
      - 开发态:        <项目根>/user_data/<subpaths>  (避免污染系统 APPDATA)

    返回:
      str  目录已自动创建.
    """
    if is_frozen():
        base = os.environ.get("APPDATA")
        if not base:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        root = os.path.join(base, APP_NAME)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root = os.path.join(project_root, "user_data")

    target = os.path.join(root, *subpaths) if subpaths else root
    try:
        os.makedirs(target, exist_ok=True)
    except OSError:
        pass
    return target
