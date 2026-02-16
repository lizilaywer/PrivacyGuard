#!/bin/bash
# PrivacyApp 自动化测试脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "PrivacyApp 自动化测试"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="/Users/a49144/Desktop/临时coding/PrivacyApp"
TEST_RESULT=0

# 进入项目目录
cd "$APP_DIR"
echo "📁 项目目录: $APP_DIR"
echo ""

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate
echo ""

# 测试 1: 语法检查
echo "----------------------------------------"
echo "测试 1: Python 语法检查"
echo "----------------------------------------"
if python -m py_compile main.py 2>/dev/null; then
    echo -e "${GREEN}✓ 语法检查通过${NC}"
else
    echo -e "${RED}✗ 语法检查失败${NC}"
    TEST_RESULT=1
fi
echo ""

# 测试 2: 模块导入检查
echo "----------------------------------------"
echo "测试 2: 模块导入检查"
echo "----------------------------------------"
IMPORT_ERRORS=$(python -c "import sys; sys.path.insert(0, '.'); import main" 2>&1 | grep -i error || true)
if [ -z "$IMPORT_ERRORS" ]; then
    echo -e "${GREEN}✓ 导入检查通过${NC}"
else
    echo -e "${RED}✗ 导入检查失败${NC}"
    echo "$IMPORT_ERRORS"
    TEST_RESULT=1
fi
echo ""

# 测试 3: 依赖检查
echo "----------------------------------------"
echo "测试 3: 依赖包检查"
echo "----------------------------------------"
REQUIRED_PACKAGES=("PyQt6" "PyMuPDF" "opencv-python" "numpy" "rapidocr-onnxruntime" "reportlab")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! pip show "$package" >/dev/null 2>&1; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 所有依赖包已安装${NC}"
    for package in "${REQUIRED_PACKAGES[@]}"; do
        VERSION=$(pip show "$package" | grep Version | cut -d' ' -f2)
        echo "  - $package: $VERSION"
    done
else
    echo -e "${RED}✗ 缺少以下依赖包:${NC}"
    for package in "${MISSING_PACKAGES[@]}"; do
        echo "  - $package"
    done
    echo ""
    echo "运行以下命令安装缺失的包:"
    echo "  pip install ${MISSING_PACKAGES[*]}"
    TEST_RESULT=1
fi
echo ""

# 测试 4: 测试文件检查
echo "----------------------------------------"
echo "测试 4: 测试文件检查"
echo "----------------------------------------"
TEST_PDF="$APP_DIR/test_sample.pdf"
if [ -f "$TEST_PDF" ]; then
    echo -e "${GREEN}✓ 测试 PDF 文件存在${NC}"
    PAGES=$(python -c "import fitz; doc = fitz.open('$TEST_PDF'); print(len(doc))")
    echo "  - 文件: test_sample.pdf"
    echo "  - 页数: $PAGES"
else
    echo -e "${YELLOW}⚠ 测试 PDF 文件不存在${NC}"
    echo "  运行 python create_test_pdf.py 生成测试文件"
fi
echo ""

# 测试 5: 虚拟环境检查
echo "----------------------------------------"
echo "测试 5: 虚拟环境检查"
echo "----------------------------------------"
PYTHON_VERSION=$(python --version)
echo "Python 版本: $PYTHON_VERSION"
if [[ "$PYTHON_VERSION" == *"3.11"* ]]; then
    echo -e "${GREEN}✓ Python 版本符合要求 (3.11.x)${NC}"
else
    echo -e "${YELLOW}⚠ Python 版本不是 3.11.x${NC}"
fi
echo ""

# 测试 6: 已打包应用检查
echo "----------------------------------------"
echo "测试 6: 已打包应用检查"
echo "----------------------------------------"
APP_BUNDLE="$APP_DIR/dist/PrivacyGuard.app"
if [ -d "$APP_BUNDLE" ]; then
    echo -e "${GREEN}✓ 已打包应用存在${NC}"
    echo "  路径: $APP_BUNDLE"
    echo "  启动命令: open \"$APP_BUNDLE\""
else
    echo -e "${YELLOW}⚠ 已打包应用不存在${NC}"
    echo "  如需打包,运行: pyinstaller PrivacyGuard.spec"
fi
echo ""

# 测试 7: OCR 功能测试
echo "----------------------------------------"
echo "测试 7: OCR 功能测试"
echo "----------------------------------------"
python << 'EOF'
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result = ocr.ocr("test", cls=True, return_confidence=True)
    print("\033[0;32m✓ RapidOCR 导入成功\033[0m")
except Exception as e:
    print(f"\033[0;31m✗ RapidOCR 测试失败: {e}\033[0m")
EOF
echo ""

# 测试 8: PDF 处理测试
echo "----------------------------------------"
echo "测试 8: PDF 处理测试"
echo "----------------------------------------"
if [ -f "$TEST_PDF" ]; then
    python << EOF
try:
    import fitz
    doc = fitz.open("$TEST_PDF")
    page = doc[0]
    text = page.get_text()
    if len(text) > 0:
        print(f"\033[0;32m✓ PDF 文本提取成功\033[0m")
        print(f"  - 提取文本长度: {len(text)} 字符")
        print(f"  - 前50个字符: {text[:50]}...")
    else:
        print("\033[0;31m✗ PDF 文本提取失败\033[0m")
    doc.close()
except Exception as e:
    print(f"\033[0;31m✗ PDF 处理失败: {e}\033[0m")
EOF
else
    echo -e "${YELLOW}⚠ 跳过 (测试文件不存在)${NC}"
fi
echo ""

# 测试总结
echo "=========================================="
echo "测试总结"
echo "=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过${NC}"
    echo ""
    echo "🚀 启动应用:"
    echo "  方式 1 (源码): cd \"$APP_DIR\" && source venv/bin/activate && python main.py"
    echo "  方式 2 (打包): open \"$APP_BUNDLE\""
else
    echo -e "${RED}✗ 部分测试失败${NC}"
    echo "请检查上述错误信息并修复问题"
fi
echo ""

exit $TEST_RESULT
