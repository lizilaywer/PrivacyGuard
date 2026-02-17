#!/bin/bash
#
# PrivacyGuard macOS 应用公证脚本
# 说明: 将应用提交到 Apple 进行公证（Notarization）
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

# 从 version.txt 读取版本号
VERSION=$(cat "${PROJECT_ROOT}/version.txt" | tr -d '[:space:]')
if [ -z "$VERSION" ]; then
    echo "错误: 无法读取 version.txt"
    exit 1
fi
RELEASE_DIR="${PROJECT_ROOT}/releases/macos"

DMG_NAME="${APP_NAME}-${VERSION}-macOS.dmg"
DMG_PATH="${RELEASE_DIR}/${DMG_NAME}"

# 检查 DMG 是否存在
if [ ! -f "${DMG_PATH}" ]; then
    echo -e "${RED}错误: 未找到 DMG 文件 ${DMG_PATH}${NC}"
    echo "请先运行 build_macos_app.sh 创建 DMG"
    exit 1
fi

# Apple ID 和临时密码（用户需要修改这里）
APPLE_ID="your-email@example.com"
APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
TEAM_ID="XXXXXXXXXX"

# 检查配置
if [[ "$APPLE_ID" == *"your-email"* ]]; then
    echo -e "${YELLOW}警告: 请修改脚本中的以下变量:${NC}"
    echo "  - APPLE_ID: 你的 Apple ID 邮箱"
    echo "  - APP_SPECIFIC_PASSWORD: 应用专用密码"
    echo "  - TEAM_ID: 开发者团队 ID"
    echo ""
    echo "应用专用密码可以在 https://appleid.apple.com 生成"
    exit 1
fi

echo -e "${BLUE}开始公证 DMG...${NC}"
echo "文件: ${DMG_PATH}"

# 提交公证
xcrun notarytool submit "${DMG_PATH}" \
    --apple-id "${APPLE_ID}" \
    --password "${APP_SPECIFIC_PASSWORD}" \
    --team-id "${TEAM_ID}" \
    --wait

# 将公证信息附加到 DMG
echo -e "${BLUE}将公证信息附加到 DMG...${NC}"
xcrun stapler staple "${DMG_PATH}"

# 验证公证
echo -e "${BLUE}验证公证...${NC}"
xcrun stapler validate "${DMG_PATH}"

# 检查公证状态
echo -e "${BLUE}公证详情:${NC}"
spctl -a -t open --context context:primary-signature -v "${DMG_PATH}" || true

echo -e "${GREEN}✅ DMG 公证完成${NC}"
echo ""
echo -e "${YELLOW}注意:${NC}"
echo "公证后的应用可以被 macOS Gatekeeper 正常打开"
echo "无需用户手动允许未知来源的应用"
