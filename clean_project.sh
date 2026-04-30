#!/bin/bash
# PrivacyGuard 项目清理脚本
# 清理临时文件，但保留旧备份
# 用法: ./clean_project.sh

set -e

echo "======================================"
echo "  PrivacyGuard 项目清理"
echo "======================================"
echo ""

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "[INFO] 项目目录: $PROJECT_DIR"
echo ""

# 清理构建输出
echo "[1/6] 清理构建输出..."
if [ -d "dist" ]; then
    rm -rf dist
    echo "      ✓ 已删除 dist/"
fi
if [ -d "build" ]; then
    rm -rf build
    echo "      ✓ 已删除 build/"
fi
echo ""

# 清理 Python 缓存
echo "[2/6] 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
echo "      ✓ 已清理 __pycache__, *.pyc, *.pyo, .DS_Store"
echo ""

# 清理测试临时文件
echo "[3/6] 清理测试临时文件..."
if [ -d "tests/temp" ]; then
    rm -rf tests/temp/*
    echo "      ✓ 已清理 tests/temp/"
fi
echo ""

# 清理日志文件（保留最近7天）
echo "[4/6] 清理旧日志文件..."
find . -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
echo "      ✓ 已删除7天前的日志"
echo ""

# 保留备份目录（重要！不删除旧备份）
echo "[5/6] 检查备份目录..."
if [ -d "backups" ]; then
    BACKUP_COUNT=$(find backups -type d -name "v*" | wc -l)
    echo "      ✓ 保留所有备份目录（共 $BACKUP_COUNT 个版本备份）"
else
    echo "      - 无备份目录"
fi
echo ""

# 统计清理后大小
echo "[6/6] 统计项目大小..."
PROJECT_SIZE=$(du -sh . | cut -f1)
echo "      项目总大小: $PROJECT_SIZE"
echo ""

echo "======================================"
echo "  清理完成！"
echo "======================================"
echo ""
echo "注意: 以下目录被保留（按用户要求）:"
echo "  - backups/      (版本备份)"
echo "  - tests/        (测试文件)"
echo "  - docs/         (开发文档)"
echo "  - packaging/    (打包配置)"
echo ""
