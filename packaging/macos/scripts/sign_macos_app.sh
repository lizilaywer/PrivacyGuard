#!/bin/bash
#
# PrivacyGuard macOS 应用签名脚本
# 说明: 使用开发者证书对应用进行签名
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_NAME="PrivacyGuard"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
APP_PATH="${PROJECT_ROOT}/dist/${APP_NAME}.app"

# 检查应用是否存在
if [ ! -d "${APP_PATH}" ]; then
    echo -e "${RED}错误: 未找到应用 ${APP_PATH}${NC}"
    echo "请先运行 build_macos_app.sh 打包应用"
    exit 1
fi

# 列出可用的签名证书
echo -e "${BLUE}可用的签名证书:${NC}"
security find-identity -v -p codesigning

echo ""
echo -e "${YELLOW}提示:${NC}"
echo "要使用签名功能，你需要："
echo "1. 拥有 Apple Developer 账号"
echo "2. 在 Xcode 中配置开发者证书"
echo "3. 将证书名称替换到下面的 CODESIGN_ID 变量"
echo ""

# 设置证书 ID（用户需要修改这里）
CODESIGN_ID="Developer ID Application: Your Name (XXXXXXXXXX)"

# 检查是否是示例证书
if [[ "$CODESIGN_ID" == *"Your Name"* ]]; then
    echo -e "${YELLOW}警告: 请修改脚本中的 CODESIGN_ID 变量为你的实际证书名称${NC}"
    echo "可以运行 'security find-identity -v -p codesigning' 查看可用证书"
    exit 1
fi

echo -e "${GREEN}开始签名应用...${NC}"

# 签名应用
codesign --force --deep --sign "${CODESIGN_ID}" \
    --entitlements "${SCRIPT_DIR}/../config/entitlements.plist" \
    "${APP_PATH}"

# 验证签名
echo -e "${BLUE}验证签名...${NC}"
codesign --verify --verbose "${APP_PATH}"

# 显示签名信息
echo -e "${BLUE}签名信息:${NC}"
codesign --display --verbose=2 "${APP_PATH}"

echo -e "${GREEN}✅ 应用签名完成${NC}"
