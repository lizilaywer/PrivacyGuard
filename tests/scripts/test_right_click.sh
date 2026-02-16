#!/bin/bash

# PrivacyApp 右键点击删除功能测试脚本

echo "================================================"
echo "PrivacyApp v19.4 - 右键点击删除功能测试"
echo "================================================"
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 关闭旧进程
echo "1. 关闭旧进程..."
pkill -f "python.*main.py" 2>/dev/null
sleep 1

# 清空日志
echo "2. 清空调试日志..."
> app_debug.log

# 启动应用
echo "3. 启动应用..."
./venv/bin/python main.py > app_debug.log 2>&1 &
APP_PID=$!
sleep 3

echo "   应用已启动 (PID: $APP_PID)"
echo ""

# 显示测试步骤
echo "================================================"
echo "测试步骤:"
echo "================================================"
echo ""
echo "1. 在应用中点击 '打开PDF' 按钮"
echo "2. 选择 test_sample.pdf"
echo "3. 点击 '智能脱敏' 按钮"
echo "4. 右键点击任意涂黑区域"
echo "5. 观察以下结果:"
echo "   ✓ 矩形框应该被删除"
echo "   ✓ 终端应显示调试信息"
echo ""
echo "================================================"
echo "实时查看日志 (Ctrl+C 退出):"
echo "================================================"
echo ""

# 实时查看日志
tail -f app_debug.log
