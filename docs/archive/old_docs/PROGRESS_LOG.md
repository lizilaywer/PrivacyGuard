=== 修复日志 ===

## v26 - 滚动位置稳定性修复
日期: 2026-02-11 16:54:40

### 已修复问题
1. ✅ 部分行无法手动脱敏（findTextPosition 改进）

### 待修复问题
2. ❌ 滚动位置跳转（使用 localStorage 自动保存/恢复）

### 修复策略
- 在页面卸载前（beforeunload）自动保存滚动位置到 localStorage
- 在页面加载时从 localStorage 恢复滚动位置
- 使用淡入动画掩盖重新加载

## v27 - 深度调试修复
日期: 2026-02-11 17:29:00

### 用户反馈问题
1. ❌ 滚动跳转问题仍然存在
2. ❌ 部分文档右键无反应

### v27 修复方案

#### 修复 1: findTextPosition 增强
- 添加超详细调试日志（带 `=========` 分隔符）
- 打印所有文本节点信息（前 10 个）
- 处理 startContainer/endContainer 是元素节点的情况
- 改进文本节点匹配逻辑（使用 `contains()` 检查）

#### 修复 2: 滚动恢复简化
- **移除淡入动画**（可能导致滚动延迟）
- **立即执行滚动恢复**（无等待）
- **二次确认滚动**（10ms 后再次执行，确保生效）
- **多重触发时机**（DOMContentLoaded, load, requestAnimationFrame）
- **添加页面可见性监听**（切换标签页时保存位置）

### 备份文件
- main.py.backup_v27_deep_fix_20260211_1729XX

### 待验证
- 滚动到最底部 → 添加脱敏 → 位置保持
- 所有文档位置右键菜单正常显示

## v28 - HTML 高亮显示修复
日期: 2026-02-11 17:41:00

### 问题描述
预览视图中显示裸露的 HTML 标签：
```
class="text-block" data-key="paragraph_0" data-original-text="协议书">协议书
```

### 根本原因
`_highlight_sensitive_info` 方法中的替换逻辑有严重 bug：
```python
html = html.replace(escape(text), highlighted_text)
```
**问题**:
1. 重复文本会全部被替换（如 "协议书" 出现多次，会全部被替换）
2. HTML 转义不匹配（mammoth 输出的 HTML 可能已部分转义）
3. 替换失败时，HTML 标签被当作文本显示

### 修复方案
使用 **占位符三遍替换策略**：

```
原始 HTML: <p>协议书</p><p>其他内容</p>
         ↓ (第一遍: 生成占位符)
占位符:   __PLACEHOLDER_paragraph_0__
         ↓ (第二遍: 文本 → 占位符)
中间 HTML:<p>__PLACEHOLDER_paragraph_0__</p><p>其他内容</p>
         ↓ (第三遍: 占位符 → 高亮内容)
最终 HTML:<p><span class="text-block"...><mark...>协议书</mark></span></p>...
```

### 代码改进
1. 为每个段落生成唯一占位符 `__PLACEHOLDER_{key}__`
2. 使用 4 种匹配方式确保替换成功：
   - 直接匹配转义后的文本
   - 匹配未转义的文本
   - 使用正则表达式宽松匹配
   - 在 `<p>` 标签内查找
3. 三遍替换避免重复替换问题

### 备份文件
- main.py.backup_v28_html_fix_20260211_1741XX

### 待验证
- 自定义关键词高亮正确显示
- 不再显示裸露的 HTML 标签
- 导出功能正常
