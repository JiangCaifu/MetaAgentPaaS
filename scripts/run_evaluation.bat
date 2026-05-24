@echo off
REM ========================================
REM 第11周任务：定期评估脚本
REM 用于定期检测Agent回答质量
REM ========================================
echo 正在运行Agent效果评估...
echo.

REM 切换到项目目录
cd C:\Users\zhaoxi\Projects\MetaAgentsPaaS

REM 运行评估脚本
"C:\Users\zhaoxi\PycharmProjects\pythonProject1\venv\Scripts\python.exe" scripts\agent_evaluation.py

echo.
echo 评估完成！
echo 报告已保存到 reports/ 目录
pause