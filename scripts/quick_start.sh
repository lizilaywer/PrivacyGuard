#!/bin/bash
# ============================================================================
# PrivacyGuard 快速启动脚本
# 提供常用开发命令的快捷方式
# ============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 打印标题
print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}        $(printf '%58s' "PrivacyGuard 快速启动")${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 打印菜单
print_menu() {
    echo -e "${GREEN}常用操作:${NC}"
    echo "  1) 启动应用           7) 查看版本"
    echo "  2) 运行测试           8) Git 状态"
    echo "  3) macOS 打包         9) 创建开发分支"
    echo "  4) 提交代码          10) 查看项目进度"
    echo "  5) 查看开发日志      11) 更新依赖"
    echo "  6) 查看当前状态      12) 退出"
    echo ""
}

# 获取版本号
get_version() {
    grep "VERSION =" main.py | sed 's/VERSION = //' | sed 's/"//g'
}

# 启动应用
start_app() {
    echo -e "${BLUE}>>> 启动 PrivacyGuard...${NC}"
    python main.py
}

# 运行测试
run_tests() {
    echo -e "${BLUE}>>> 运行测试...${NC}"

    if [ -f "tests/scripts/test_stability.py" ]; then
        python tests/scripts/test_stability.py
    else
        echo -e "${YELLOW}测试文件不存在，跳过${NC}"
    fi
}

# macOS 打包
build_macos() {
    echo -e "${BLUE}>>> macOS 打包...${NC}"
    bash packaging/macos/scripts/build_macos_app.sh
}

# 查看版本
show_version() {
    echo -e "${CYAN}当前版本: $(get_version)${NC}"
}

# Git 状态
git_status() {
    echo -e "${BLUE}>>> Git 状态${NC}"
    echo ""
    git status
    echo ""
    echo "最近提交:"
    git log -1 --oneline
}

# 提交代码
commit_code() {
    echo -e "${BLUE}>>> 提交代码${NC}"
    echo ""
    git add .
    echo ""
    echo -e "${YELLOW}请输入提交信息:${NC}"
    read -p "> " commit_msg
    echo ""
    git commit -m "$commit_msg"
    echo ""
    echo -e "${GREEN}✓ 代码已提交${NC}"
}

# 查看开发日志
show_devlog() {
    echo -e "${BLUE}>>> 开发日志 (最近 20 行)${NC}"
    echo ""
    if [ -f "docs/DEV_LOG.md" ]; then
        head -n 20 docs/DEV_LOG.md
    else
        echo -e "${YELLOW}开发日志不存在${NC}"
    fi
}

# 查看状态
show_status() {
    echo -e "${BLUE}>>> 项目状态${NC}"
    echo ""
    if [ -f "docs/STATUS.md" ]; then
        head -n 30 docs/STATUS.md
    else
        echo -e "${YELLOW}状态文件不存在${NC}"
    fi
}

# 创建开发分支
create_branch() {
    echo -e "${BLUE}>>> 创建开发分支${NC}"
    echo ""
    echo -e "${YELLOW}当前版本: $(get_version)${NC}"
    echo ""
    read -p "请输入新版本号 (如 36.0): " new_version
    echo ""
    branch_name="dev-v$new_version"

    echo -e "${BLUE}创建分支: $branch_name${NC}"
    git checkout -b "$branch_name"

    echo ""
    echo -e "${GREEN}✓ 分支已创建: $branch_name${NC}"
    echo ""
    echo "下一步:"
    echo "  1. 编辑 main.py 更新版本号"
    echo "  2. 进行开发和测试"
    echo "  3. 提交代码"
}

# 查看项目进度
show_progress() {
    echo -e "${BLUE}>>> 项目进度${NC}"
    echo ""
    if [ -f "scripts/check_progress.py" ]; then
        python scripts/check_progress.py
    else
        echo -e "${YELLOW}进度检查脚本不存在${NC}"
    fi
}

# 更新依赖
update_deps() {
    echo -e "${BLUE}>>> 更新依赖${NC}"
    echo ""
    pip install --upgrade -r requirements.txt
    echo ""
    echo -e "${GREEN}✓ 依赖已更新${NC}"
}

# 主循环
main() {
    print_header

    # 显示版本
    show_version
    echo ""

    # 如果有参数，直接执行
    if [ $# -gt 0 ]; then
        case "$1" in
            start|run)      start_app ;;
            test)           run_tests ;;
            build)          build_macos ;;
            commit)         commit_code ;;
            log)            show_devlog ;;
            status)         show_status ;;
            progress)       show_progress ;;
            *)              echo "未知命令: $1" ;;
        esac
        exit 0
    fi

    # 交互式菜单
    while true; do
        print_menu
        read -p "请选择操作 [1-12]: " choice
        echo ""

        case $choice in
            1) start_app ;;
            2) run_tests ;;
            3) build_macos ;;
            4) commit_code ;;
            5) show_devlog ;;
            6) show_status ;;
            7) show_version ;;
            8) git_status ;;
            9) create_branch ;;
            10) show_progress ;;
            11) update_deps ;;
            12) echo "再见！"; exit 0 ;;
            *) echo -e "${RED}无效选择${NC}" ;;
        esac

        echo ""
        read -p "按 Enter 继续..."
        echo ""
    done
}

# 运行主程序
main "$@"
