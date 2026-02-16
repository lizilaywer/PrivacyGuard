# PrivacyGuard v22.1 快速测试指南

## 🚀 一键启动

```bash
cd /Users/a49144/Desktop/临时coding/PrivacyApp
source venv/bin/activate
python main.py
```

## ⭐ 核心测试（30秒）

### 1. 导入 PDF（5秒）
- 点击 "📂 打开"
- 选择 `test_sample.pdf`

### 2. 智能脱敏（10秒）
- 点击 "⚙️ 高级设置"
- 勾选 "身份证号" 和 "手机号码"
- 点击 "🔍 智能脱敏"
- 等待完成

### 3. 右键删除（重点！）（5秒）
- **在脱敏框上右键点击**
- ✅ 成功：脱敏框消失，控制台有日志
- ❌ 失败：无反应，无日志

### 4. 手动标记删除（10秒）
- 拖拽绘制矩形框
- **在矩形框上右键点击**
- ✅ 成功：矩形框消失
- ❌ 失败：无反应

## ✅ 预期控制台输出

```
[DEBUG] MainWindow.eventFilter 捕获右键点击！
[DEBUG] 点击位置 (相对container): (234.56, 456.78)
[DEBUG] 左canvas几何: x=10, y=10, w=800, h=1000
[DEBUG] 映射到左canvas: (224.56, 446.78)
[DEBUG] === 右键点击删除 (eventFilter) ===
[DEBUG] 页面索引: 0
[DEBUG] 点击位置: (224.56, 446.78)
[DEBUG] ✓ 删除XXX框: 页面0, 索引X
```

## 📋 测试结果

- [ ] 导入 PDF 成功
- [ ] 智能脱敏成功
- [ ] **右键删除 OCR 框成功** ← 最重要
- [ ] **右键删除手动框成功** ← 最重要
- [ ] 左键绘制正常

## 📝 发现问题？

1. 截图控制台日志
2. 记录操作步骤
3. 反馈给开发人员

---

**版本**: v22.1 - Viewport Filter
**修复**: 将事件过滤器从 canvas_container 移动到 scroll.viewport()
