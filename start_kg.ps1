<#
=========================================
第9周学习任务启动脚本（PowerShell）
=========================================
功能：
1. 运行知识图谱构建脚本
2. 运行测试脚本
3. 启动FastAPI服务
=========================================
#>

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "🎯 第9周学习任务：文旅知识图谱" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

# 步骤1：运行知识图谱构建脚本
Write-Host "📦 步骤1：构建知识图谱..." -ForegroundColor Yellow
python agent/graph/kg_service.py
Write-Host "`n✅ 知识图谱构建完成！`n" -ForegroundColor Green

# 步骤2：运行测试脚本
Write-Host "🧪 步骤2：运行测试..." -ForegroundColor Yellow
python test_kg.py
Write-Host "`n✅ 测试完成！`n" -ForegroundColor Green

# 步骤3：启动FastAPI服务
Write-Host "🚀 步骤3：启动FastAPI服务..." -ForegroundColor Yellow
Write-Host "服务地址：http://localhost:8000/docs" -ForegroundColor White
Write-Host "按 Ctrl+C 停止服务`n" -ForegroundColor Gray

# 启动服务
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info