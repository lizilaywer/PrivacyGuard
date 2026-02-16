#!/bin/bash
# PrivacyApp 快速测试和启动脚本

set -e

APP_DIR="/Users/a49144/Desktop/临时coding/PrivacyApp"
cd "$APP_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}PrivacyApp 快速测试和启动${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# 激活虚拟环境
source venv/bin/activate

# 快速健康检查
echo -e "${YELLOW}🔍 快速健康检查...${NC}"

# 检查 Python
python --version

# 检查关键依赖
echo -e "\n${GREEN}✓ 依赖包状态:${NC}"
pip list | grep -E "(PyQt6|PyMuPDF|RapidOCR)" || echo "部分依赖缺失"

# 检查测试文件
if [ -f "test_sample.pdf" ]; then
    echo -e "${GREEN}✓ 测试文件: test_sample.pdf${NC}"
else
    echo -e "${YELLOW}⚠ 测试文件不存在,正在生成...${NC}"
    python create_test_pdf.py
fi

echo ""
echo "请选择操作:"
echo "1) 运行完整自动化测试"
echo "2) 启动应用 (源码模式)"
echo "3) 启动应用 (打包模式)"
echo "4) 仅运行健康检查"
echo "5) 退出"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo -e "${BLUE}运行完整测试...${NC}"
        bash test.sh
        ;;
    2)
        echo -e "${BLUE}启动应用 (源码模式)...${NC}"
        echo "提示: 使用 Ctrl+C 退出应用"
        python main.py
        ;;
    3)
        echo -e "${BLUE}启动应用 (打包模式)...${NC}"
        open "dist/PrivacyGuard.app"
        echo "应用已启动,请在 macOS 中使用"
        ;;
    4)
        echo -e "${GREEN}✓ 健康检查完成${NC}"
        ;;
    5)
        echo "退出"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
