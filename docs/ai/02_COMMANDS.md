# 02 - 运行 / 打包 / 调试命令

> ⚠️ 本项目开发环境是 **Windows + PowerShell 7+**，全部命令使用 PowerShell 语法。

---

## 1. 环境准备

```powershell
# 建议 Python 3.10 / 3.11 x64
python --version

# 安装依赖（锁定版本）
python -m pip install -r requirements.txt

# 或使用 pyproject 安装
python -m pip install -e .
```

## 2. 运行

```powershell
# 启动主程序（源码）
python main.py
```

### 切换日志级别

在 [main.py:L27-L31](file:///d:/CodeProject/TRAE_Projects/KK_Lab/main.py#L27-L31) 中改：

```python
setup_logging(level=logging.DEBUG)    # 全部输出
setup_logging(level=logging.INFO)     # 默认
setup_logging(level=logging.WARNING)  # 仅警告和错误
setup_logging(level=logging.ERROR)    # 仅错误
```

### 开启 Mock 模式（无硬件调试）

在 [debug_config.py](file:///d:/CodeProject/TRAE_Projects/KK_Lab/debug_config.py) 中：

```python
DEBUG_MOCK = True
```

## 3. 打包

```powershell
# 主程序
python -m PyInstaller spec/kk_lab.spec --clean --noconfirm

# N6705C Datalog 独立工具
python -m PyInstaller spec/n6705c_datalog.spec --clean --noconfirm
```

打包产物默认在 `dist/` 目录。

## 4. 清理

```powershell
# 清理打包产物
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 清理 __pycache__
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

## 5. 查找仪器资源

使用 Python 快速列出 VISA 资源：

```powershell
python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
```

列出串口：

```powershell
python -c "from serial.tools import list_ports; [print(p.device, p.description) for p in list_ports.comports()]"
```

## 6. 常用调试

```powershell
# 在 Mock 模式下启动（需先设 DEBUG_MOCK=True）
python main.py

# 仅跑 I2C Demo
python lib/i2c/i2c_demo_x64.py
```

## 7. 质量检查（可选 / 若添加）

目前项目**未**配置 lint / type-check 命令。如需引入建议：

```powershell
# 如果后续加了 ruff
ruff check .

# 如果后续加了 mypy
mypy main.py
```

若新增命令，请更新本文件 + [CLAUDE.md](../../CLAUDE.md)。

## 8. Git 常用

```powershell
git status
git diff
git log -n 20 --oneline
```

> ⚠️ **禁止** AI 自行 `git commit` / `git push`，必须用户明确指示才执行。
