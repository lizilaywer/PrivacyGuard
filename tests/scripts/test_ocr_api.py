#!/usr/bin/env python3
"""测试 RapidOCR API"""

from rapidocr_onnxruntime import RapidOCR

# 测试正确的 API
ocr = RapidOCR()
print("RapidOCR 已创建")
print(f"类型: {type(ocr)}")
print(f"方法: {[m for m in dir(ocr) if not m.startswith('_')]}")

# 测试实际的 OCR
import fitz

# 从 PDF 提取图像进行测试
pdf_path = "/Users/a49144/Desktop/临时coding/PrivacyApp/test_sample.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

# 将页面转换为图像
pix = page.get_pixmap()
img_data = pix.tobytes("png")

# 保存临时图像
with open("/tmp/test_page.png", "wb") as f:
    f.write(img_data)

print("\n测试 OCR 识别...")
# 正确的 API 调用
result = ocr("/tmp/test_page.png")

if result and len(result) > 0:
    print(f"✓ OCR 识别成功")
    print(f"识别到 {len(result)} 个文本块")
    for item in result[:3]:  # 只显示前3个
        print(f"  - {item}")
else:
    print("⚠ 未识别到文本")

doc.close()
