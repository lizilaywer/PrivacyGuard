#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrivacyGuard 项目进度查询工具
快速获取版本信息、Git 状态和开发进度
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime


class ProgressChecker:
    """进度检查器"""

    def __init__(self):
        """初始化"""
        self.project_root = Path(__file__).parent.parent

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 70)
        print(f"  {title}".center(70))
        print("=" * 70 + "\n")

    def get_version(self) -> str:
        """获取版本号"""
        main_py = self.project_root / "main.py"

        try:
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'VERSION = "(.*?)"', content)
                if match:
                    return match.group(1)
        except Exception as e:
            return f"Error: {e}"

        return "Unknown"

    def get_git_info(self) -> dict:
        """获取 Git 信息"""
        git_info = {
            'branch': 'Unknown',
            'commit': 'Unknown',
            'status': '',
            'tags': []
        }

        try:
            # 获取当前分支
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True, text=True, cwd=self.project_root
            )
            git_info['branch'] = result.stdout.strip() if result.returncode == 0 else 'Not a git repo'

            # 获取最新 commit
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%h'],
                capture_output=True, text=True, cwd=self.project_root
            )
            git_info['commit'] = result.stdout.strip() if result.returncode == 0 else 'Unknown'

            # 获取工作区状态
            result = subprocess.run(
                ['git', 'status', '--short'],
                capture_output=True, text=True, cwd=self.project_root
            )
            git_info['status'] = result.stdout.strip() if result.returncode == 0 else ''

            # 获取标签
            result = subprocess.run(
                ['git', 'tag', '--sort=-v:refname'],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                git_info['tags'] = result.stdout.strip().split('\n')[:5]

        except Exception as e:
            git_info['branch'] = f"Error: {e}"

        return git_info

    def get_file_stats(self) -> dict:
        """获取文件统计"""
        stats = {
            'main_py_size': 0,
            'main_py_lines': 0,
            'total_py_files': 0
        }

        try:
            # main.py 统计
            main_py = self.project_root / "main.py"
            if main_py.exists():
                stats['main_py_size'] = main_py.stat().st_size / 1024  # KB
                with open(main_py, 'r', encoding='utf-8') as f:
                    stats['main_py_lines'] = len(f.readlines())

            # Python 文件总数
            stats['total_py_files'] = len(list(self.project_root.rglob("*.py")))

        except Exception as e:
            pass

        return stats

    def get_dev_status(self) -> str:
        """获取开发状态（从 STATUS.md）"""
        status_file = self.project_root / "docs" / "STATUS.md"

        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 返回前 10 行作为预览
                    return ''.join(lines[:10])
            except:
                pass

        return ""

    def print_version_info(self):
        """打印版本信息"""
        print("📦 版本信息")
        print("─" * 70)
        version = self.get_version()
        print(f"  当前版本: {version}")
        print()

    def print_git_info(self):
        """打印 Git 信息"""
        print("🔧 Git 状态")
        print("─" * 70)
        git_info = self.get_git_info()

        print(f"  当前分支: {git_info['branch']}")
        print(f"  最新提交: {git_info['commit']}")

        if git_info['status']:
            print(f"  工作区状态: 有未提交的更改")
            print(f"    {git_info['status'][:50]}...")
        else:
            print(f"  工作区状态: 干净")

        if git_info['tags'] and git_info['tags'][0]:
            print(f"  最近标签: {', '.join(git_info['tags'][:3])}")

        print()

    def print_file_stats(self):
        """打印文件统计"""
        print("📊 代码统计")
        print("─" * 70)
        stats = self.get_file_stats()

        print(f"  main.py: {stats['main_py_lines']:,} 行 ({stats['main_py_size']:.1f} KB)")
        print(f"  Python 文件总数: {stats['total_py_files']}")
        print()

    def print_next_steps(self):
        """打印下一步建议"""
        print("📝 下一步操作")
        print("─" * 70)
        print("  开发相关:")
        print("    • 启动应用:     python main.py")
        print("    • 运行测试:     python tests/scripts/test_stability.py")
        print("    • 查看日志:     cat docs/DEV_LOG.md")
        print()
        print("  发布相关:")
        print("    • macOS 打包:   bash build/build_macos_app.sh")
        print("    • Windows 打包: packaging/windows/scripts/2_一键打包.bat (在 Windows 上)")
        print()
        print("  文档相关:")
        print("    • 项目状态:     cat docs/STATUS.md")
        print("    • 开发流程:     cat docs/DEVELOPMENT_WORKFLOW.md")
        print("    • 更新日志:     cat CHANGELOG.md")
        print()

    def print_quick_commands(self):
        """打印快速命令"""
        print("⚡ 快速命令")
        print("─" * 70)
        print("  查看版本号:")
        print("    grep VERSION main.py")
        print()
        print("  创建新分支:")
        print("    git checkout -b dev-v36")
        print()
        print("  提交更改:")
        print("    git add . && git commit -m '描述'")
        print()
        print("  查看更改:")
        print("    git diff")
        print()
        print("  运行应用:")
        print("    python main.py")
        print()

    def run(self):
        """运行检查"""
        self.print_header("PrivacyGuard 项目进度")

        # 打印各种信息
        self.print_version_info()
        self.print_git_info()
        self.print_file_stats()
        self.print_next_steps()
        self.print_quick_commands()

        # 开发状态预览
        dev_status = self.get_dev_status()
        if dev_status:
            print("📋 开发状态预览 (docs/STATUS.md)")
            print("─" * 70)
            print(dev_status)
            print("  ...(更多)")
            print()

        print("=" * 70)
        print(f"  查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(70))
        print("=" * 70 + "\n")


def main():
    """主函数"""
    checker = ProgressChecker()
    checker.run()


if __name__ == "__main__":
    main()
