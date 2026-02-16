#!/usr/bin/env python3
"""
验证滚动位置修复的代码检查脚本
检查 WebViewBridge 类和 render_word_preview 方法是否正确实现了滚动位置保存和恢复
"""

import ast
import re

def read_file(filepath):
    """读取文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def check_webview_bridge(content):
    """检查 WebViewBridge 类是否正确实现"""
    print("=" * 60)
    print("检查 1: WebViewBridge 类扩展")
    print("=" * 60)

    checks = {
        '_scroll_position': False,
        '_pending_scroll_restore': False,
        'get_scroll_position': False,
        'set_scroll_position': False,
        'clear_pending_scroll_restore': False,
        'has_pending_scroll_restore': False,
    }

    # 检查属性
    if 'self._scroll_position = 0' in content:
        checks['_scroll_position'] = True
        print("  ✓ _scroll_position 属性已定义")
    else:
        print("  ✗ _scroll_position 属性未找到")

    if 'self._pending_scroll_restore = False' in content:
        checks['_pending_scroll_restore'] = True
        print("  ✓ _pending_scroll_restore 属性已定义")
    else:
        print("  ✗ _pending_scroll_restore 属性未找到")

    # 检查方法
    if 'def get_scroll_position(self):' in content:
        checks['get_scroll_position'] = True
        print("  ✓ get_scroll_position() 方法已定义")
    else:
        print("  ✗ get_scroll_position() 方法未找到")

    if 'def set_scroll_position(self, position):' in content:
        checks['set_scroll_position'] = True
        print("  ✓ set_scroll_position() 方法已定义")
    else:
        print("  ✗ set_scroll_position() 方法未找到")

    if 'def clear_pending_scroll_restore(self):' in content:
        checks['clear_pending_scroll_restore'] = True
        print("  ✓ clear_pending_scroll_restore() 方法已定义")
    else:
        print("  ✗ clear_pending_scroll_restore() 方法未找到")

    if 'def has_pending_scroll_restore(self):' in content:
        checks['has_pending_scroll_restore'] = True
        print("  ✓ has_pending_scroll_restore() 方法已定义")
    else:
        print("  ✗ has_pending_scroll_restore() 方法未找到")

    passed = sum(checks.values())
    total = len(checks)
    print(f"\n结果: {passed}/{total} 项通过")
    return passed == total

def check_render_word_preview(content):
    """检查 render_word_preview 方法是否正确实现"""
    print("\n" + "=" * 60)
    print("检查 2: render_word_preview() 方法修改")
    print("=" * 60)

    checks = {
        'save_scroll_js': False,
        'save_callback': False,
        'restore_callback': False,
        'loadFinished_signal': False,
        'scroll_restore_js': False,
    }

    # 检查保存滚动位置的 JavaScript
    if '[PythonRestore] 保存滚动位置:' in content:
        checks['save_scroll_js'] = True
        print("  ✓ 保存滚动位置的 JavaScript 代码已添加")
    else:
        print("  ✗ 保存滚动位置的 JavaScript 代码未找到")

    # 检查保存回调函数
    if 'def save_scroll_position(scroll_result):' in content:
        checks['save_callback'] = True
        print("  ✓ save_scroll_position() 回调函数已定义")
    else:
        print("  ✗ save_scroll_position() 回调函数未找到")

    # 检查恢复回调函数
    if 'def restore_scroll_on_load(ok):' in content:
        checks['restore_callback'] = True
        print("  ✓ restore_scroll_on_load() 回调函数已定义")
    else:
        print("  ✗ restore_scroll_on_load() 回调函数未找到")

    # 检查 loadFinished 信号连接
    if 'self.word_preview.loadFinished.connect(restore_scroll_on_load)' in content:
        checks['loadFinished_signal'] = True
        print("  ✓ loadFinished 信号连接已设置")
    else:
        print("  ✗ loadFinished 信号连接未找到")

    # 检查恢复滚动位置的 JavaScript
    if '[PythonRestore] 恢复滚动位置:' in content:
        checks['scroll_restore_js'] = True
        print("  ✓ 恢复滚动位置的 JavaScript 代码已添加")
    else:
        print("  ✗ 恢复滚动位置的 JavaScript 代码未找到")

    passed = sum(checks.values())
    total = len(checks)
    print(f"\n结果: {passed}/{total} 项通过")
    return passed == total

def check_timing_solution(content):
    """检查时序问题解决方案"""
    print("\n" + "=" * 60)
    print("检查 3: 时序问题解决方案")
    print("=" * 60)

    # 检查是否使用 runJavaScript 异步获取位置
    has_async_save = 'self.word_preview.page().runJavaScript(scroll_save_js' in content
    # 检查是否在 loadFinished 中恢复
    has_restore_on_load = 'restore_scroll_on_load' in content
    # 检查是否有双重确认机制
    has_double_confirm = 'setTimeout(function()' in content and 'window.scrollTo(0, targetY)' in content

    if has_async_save:
        print("  ✓ 使用 runJavaScript 异步获取滚动位置")
    else:
        print("  ✗ 未使用 runJavaScript 异步获取")

    if has_restore_on_load:
        print("  ✓ 在 loadFinished 信号中恢复位置")
    else:
        print("  ✗ 未在 loadFinished 中恢复")

    if has_double_confirm:
        print("  ✓ 使用双重确认机制")
    else:
        print("  ✗ 未使用双重确认")

    passed = sum([has_async_save, has_restore_on_load, has_double_confirm])
    print(f"\n结果: {passed}/3 项通过")
    return passed == 3

def check_version_update(content):
    """检查版本号是否更新"""
    print("\n" + "=" * 60)
    print("检查 4: 版本号更新")
    print("=" * 60)

    version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
    if version_match:
        version = version_match.group(1)
        if '29.0' in version and 'Scroll Position Fix' in version:
            print(f"  ✓ 版本号已更新: {version}")
            return True
        else:
            print(f"  ⚠ 版本号: {version} (可能不是预期版本)")
            return '29.0' in version
    else:
        print("  ✗ 未找到版本号")
        return False

def main():
    """主函数"""
    filepath = 'main.py'

    print("\n" + "🔍 PrivacyGuard 滚动位置修复验证")
    print("=" * 60)

    try:
        content = read_file(filepath)

        # 语法检查
        print("\n语法检查...")
        try:
            ast.parse(content)
            print("  ✓ 语法正确")
        except SyntaxError as e:
            print(f"  ✗ 语法错误: {e}")
            return

        # 执行各项检查
        results = {
            'WebViewBridge 类扩展': check_webview_bridge(content),
            'render_word_preview 方法修改': check_render_word_preview(content),
            '时序问题解决方案': check_timing_solution(content),
            '版本号更新': check_version_update(content),
        }

        # 汇总结果
        print("\n" + "=" * 60)
        print("📊 验证结果汇总")
        print("=" * 60)

        for name, passed in results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {status}  {name}")

        total_passed = sum(results.values())
        total_tests = len(results)

        print(f"\n总计: {total_passed}/{total_tests} 项通过")

        if total_passed == total_tests:
            print("\n🎉 所有检查通过！代码修改正确。")
            print("\n请按照以下步骤进行手动测试:")
            print("  1. 启动应用: python main.py")
            print("  2. 打开 Word 文档")
            print("  3. 滚动到底部")
            print("  4. 选择文本并添加脱敏")
            print("  5. 验证滚动位置是否保持")
        else:
            print("\n⚠️  部分检查未通过，请检查代码。")

    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 未找到")
        print("请确保在正确的目录下运行此脚本")

if __name__ == '__main__':
    main()
