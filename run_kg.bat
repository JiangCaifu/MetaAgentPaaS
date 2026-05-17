@echo off
echo =========================================
echo 🎯 第9周学习任务：文旅知识图谱
echo =========================================
echo.

:: 尝试多种Python路径
echo 正在查找Python...

:: 尝试系统Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 找到系统Python
    python agent/graph/kg_service.py
    goto :END
)

:: 尝试用户目录Python
"%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 找到用户目录Python
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" agent/graph/kg_service.py
    goto :END
)

:: 尝试Program Files Python
"C:\Program Files\Python310\python.exe" --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 找到Program Files Python
    "C:\Program Files\Python310\python.exe" agent/graph/kg_service.py
    goto :END
)

:: 尝试Python Launcher
py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 找到Python Launcher
    py agent/graph/kg_service.py
    goto :END
)

echo ❌ 未找到Python，请检查Python安装
pause

:END
echo.
echo ✅ 运行完成
pause