#!/bin/bash
#
# PrivacyGuard macOS 应用签名脚本
# 说明: 使用开发者证书对应用进行签名
#

set -euo pipefail

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
ENTITLEMENTS_PATH="${PROJECT_ROOT}/packaging/macos/config/entitlements.plist"
CODESIGN_ID="${PRIVACYGUARD_CODESIGN_IDENTITY:-${CODESIGN_IDENTITY:-}}"

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
echo "3. 通过环境变量 PRIVACYGUARD_CODESIGN_IDENTITY 传入证书名称"
echo ""

if [ -z "${CODESIGN_ID}" ]; then
    echo -e "${YELLOW}警告: 未设置 PRIVACYGUARD_CODESIGN_IDENTITY${NC}"
    echo "示例：export PRIVACYGUARD_CODESIGN_IDENTITY='Developer ID Application: Your Name (TEAMID)'"
    echo "可以运行 'security find-identity -v -p codesigning' 查看可用证书"
    exit 1
fi

echo -e "${GREEN}开始签名应用...${NC}"
echo "证书: ${CODESIGN_ID}"

# 清理旧签名
codesign --remove-signature "${APP_PATH}" 2>/dev/null || true

# 签名应用
codesign --force --deep --options runtime --sign "${CODESIGN_ID}" \
    --entitlements "${ENTITLEMENTS_PATH}" \
    "${APP_PATH}"

# 验证签名
echo -e "${BLUE}验证签名...${NC}"
codesign --verify --verbose "${APP_PATH}"

# 显示签名信息
echo -e "${BLUE}签名信息:${NC}"
codesign --display --verbose=2 "${APP_PATH}"
spctl -a -vv "${APP_PATH}" || true

echo -e "${GREEN}应用签名完成${NC}"
