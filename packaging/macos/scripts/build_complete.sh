#!/bin/bash
# PrivacyGuard 完整打包脚本 (macOS)
# 包含清理、构建、清理打包目录、创建 DMG

set -e

echo "======================================"
echo "  PrivacyGuard 完整打包脚本 (macOS)"
echo "  版本: v37.4.1"
echo "======================================"
echo ""

# 获取项目目录
PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_DIR"

APP_NAME="PrivacyGuard"
VERSION=$(cat "$PROJECT_DIR/version.txt")
DIST_DIR="$PROJECT_DIR/dist"
RELEASE_DIR="$PROJECT_DIR/releases/macos"
CONFIG_DIR="$PROJECT_DIR/packaging/macos/config"

echo "[INFO] 应用名称: $APP_NAME"
echo "[INFO] 版本: $VERSION"
echo "[INFO] 项目目录: $PROJECT_DIR"
echo ""

# ========== 阶段 1: 环境检查 ==========
echo "[阶段 1/7] 环境检查..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "[ERROR] 虚拟环境不存在!"
    exit 1
fi
if [ ! -f "$CONFIG_DIR/PrivacyGuard.spec" ]; then
    echo "[ERROR] PyInstaller spec 文件不存在!"
    exit 1
fi
# 检查 create-dmg 是否安装
if ! command -v create-dmg &> /dev/null; then
    echo "[WARN] create-dmg 未安装，将只生成 .app 而不生成 DMG"
    echo "       安装: brew install create-dmg"
    CREATE_DMG_AVAILABLE=false
else
    CREATE_DMG_AVAILABLE=true
fi
echo "[OK] 环境检查通过"
echo ""

# ========== 阶段 2: 清理旧构建 ==========
echo "[阶段 2/7] 清理旧构建..."
if [ -d "$DIST_DIR" ]; then
    rm -rf "$DIST_DIR"
    echo "[OK] 已删除旧 dist/"
fi
if [ -d "$PROJECT_DIR/build" ]; then
    rm -rf "$PROJECT_DIR/build"
    echo "[OK] 已删除旧 build/"
fi
mkdir -p "$RELEASE_DIR"
echo ""

# ========== 阶段 3: 构建应用 ==========
echo "[阶段 3/7] 构建应用..."
echo "[INFO] 这可能需要 5-15 分钟，请等待..."
echo ""

source "$PROJECT_DIR/venv/bin/activate"
pyinstaller --clean --noconfirm "$CONFIG_DIR/PrivacyGuard.spec"

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] 构建失败!"
    exit 1
fi
echo "[OK] 构建完成"
echo ""

# ========== 阶段 4: 验证应用 ==========
echo "[阶段 4/7] 验证应用..."
APP_PATH="$DIST_DIR/$APP_NAME.app"

if [ ! -d "$APP_PATH" ]; then
    echo "[ERROR] 应用构建失败: $APP_PATH 不存在"
    exit 1
fi

# 检查关键文件
echo "[VERIFY] 检查关键文件..."
if [ -f "$APP_PATH/Contents/MacOS/$APP_NAME" ]; then
    echo "  [OK] 主可执行文件存在"
else
    echo "  [FAIL] 主可执行文件不存在"
    exit 1
fi

if [ -f "$APP_PATH/Contents/Resources/assets/donate_qrcode.png" ]; then
    echo "  [OK] assets/donate_qrcode.png 存在"
else
    echo "  [WARN] assets/donate_qrcode.png 不存在 (打赏功能将不可用)"
fi

echo "[OK] 验证通过"
echo ""

# ========== 阶段 5: 清理应用包 ==========
echo "[阶段 5/7] 清理应用包（删除重复/不需要的文件）..."

# 删除 Python 缓存
find "$APP_PATH" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_PATH" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$APP_PATH" -type f -name "*.pyo" -delete 2>/dev/null || true
echo "  [CLEAN] 清理 __pycache__, *.pyc, *.pyo"

# 删除开发/调试文件
for file in .gitignore .project_info; do
    if [ -f "$APP_PATH/Contents/Resources/$file" ]; then
        rm -f "$APP_PATH/Contents/Resources/$file"
        echo "  [CLEAN] 删除 $file"
    fi
done

# 删除不必要的测试文件
if [ -d "$APP_PATH/Contents/Resources/tests" ]; then
    rm -rf "$APP_PATH/Contents/Resources/tests"
    echo "  [CLEAN] 删除 tests/ 目录"
fi

echo "[OK] 应用包清理完成"
echo ""

# ========== 阶段 6: 签名和验证 ==========
echo "[阶段 6/7] 签名和验证..."

# 移除 quarantine 属性（如果存在）
xattr -cr "$APP_PATH" 2>/dev/null || true
echo "  [OK] 移除 quarantine 属性"

# 验证签名（如果存在开发者证书）
if security find-identity -v -p codesigning 2>/dev/null | grep -q "Developer"; then
    echo "  [INFO] 检测到开发者证书，尝试签名..."
    codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true
    echo "  [OK] 已使用临时签名"
else
    echo "  [INFO] 无开发者证书，使用临时签名"
    codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true
fi

# 显示应用大小
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
echo "[INFO] 应用大小: $APP_SIZE"
echo ""

# ========== 阶段 7: 创建 DMG ==========
echo "[阶段 7/7] 创建发布文件..."

if [ "$CREATE_DMG_AVAILABLE" = true ]; then
    DMG_NAME="${APP_NAME}-v${VERSION}-macOS.dmg"
    echo "[INFO] 创建 DMG 文件..."

    create-dmg \
        --volname "$APP_NAME" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --app-drop-link 600 185 \
        --icon "$APP_NAME.app" 200 185 \
        --hide-extension "$APP_NAME.app" \
        "$RELEASE_DIR/$DMG_NAME" \
        "$APP_PATH" \
        2>/dev/null || true

    if [ -f "$RELEASE_DIR/$DMG_NAME" ]; then
        echo "[OK] DMG 创建成功: releases/macos/$DMG_NAME"
        DMG_SIZE=$(du -sh "$RELEASE_DIR/$DMG_NAME" | cut -f1)
        echo "[INFO] DMG 大小: $DMG_SIZE"

        # 生成校验和
        echo "[INFO] 生成 SHA256 校验和..."
        shasum -a 256 "$RELEASE_DIR/$DMG_NAME" > "$RELEASE_DIR/$DMG_NAME.sha256"
        echo "[OK] 校验和已保存"
    else
        echo "[WARN] DMG 创建失败，将复制 .app 到 release 目录"
        cp -R "$APP_PATH" "$RELEASE_DIR/"
    fi
else
    echo "[INFO] create-dmg 不可用，复制 .app 到 release 目录"
    cp -R "$APP_PATH" "$RELEASE_DIR/"
    echo "[OK] 应用已复制到 releases/macos/"
fi

echo ""

# ========== 完成 ==========
echo "======================================"
echo "  [OK] 打包完成!"
echo "======================================"
echo ""
echo "输出文件:"
if [ "$CREATE_DMG_AVAILABLE" = true ] && [ -f "$RELEASE_DIR/$DMG_NAME" ]; then
    echo "  - DMG 安装包: releases/macos/$DMG_NAME"
    echo "  - 校验和: releases/macos/$DMG_NAME.sha256"
else
    echo "  - 应用包: releases/macos/$APP_NAME.app"
fi
echo ""
echo "使用说明:"
echo "  1. DMG: 双击挂载，拖拽到 Applications 文件夹"
echo "  2. APP: 直接双击运行"
echo "  3. 首次运行需在系统偏好设置中允许"
echo ""

# 询问是否测试
read -p "是否立即测试运行? (y/n): " TEST_NOW
if [[ $TEST_NOW == "y" || $TEST_NOW == "Y" ]]; then
    echo ""
    echo "[TEST] 启动测试..."
    open "$APP_PATH"
fi

echo ""
