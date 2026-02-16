#!/usr/bin/env python3
"""创建测试 PDF 文件"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_test_pdf():
    """创建包含测试数据的 PDF"""
    output_file = "/Users/a49144/Desktop/临时coding/PrivacyApp/test_sample.pdf"

    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4

    # 标题
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, height - 100, "PrivacyGuard 脱敏测试文档")

    # 内容
    c.setFont("Helvetica", 14)
    y_position = height - 150
    line_height = 30

    content = [
        "",
        "测试人员信息",
        "-" * 30,
        "姓名: 张三",
        "身份证号: 340102199001011234",
        "手机号码: 13812345678",
        "电子邮箱: test@example.com",
        "",
        "银行卡信息",
        "-" * 30,
        "中国银行: 6222021234567890123",
        "建设银行: 621700123456789012",
        "工商银行: 622200123456789012345",
        "",
        "其他信息",
        "-" * 30,
        "出生日期: 1990年1月1日",
        "入职日期: 2024年1月1日",
        "联系地址: 北京市朝阳区某某街道123号",
        "备用电话: 021-12345678",
        "",
        "重要日期",
        "-" * 30,
        "合同到期: 2025年12月31日",
        "项目启动: 2024-03-15",
        "报告提交: 2024/06/30",
        "",
        "测试说明",
        "-" * 30,
        "本文档用于测试 PrivacyGuard 的",
        "智能脱敏功能。",
        "请确保以上所有敏感信息",
        "都能被正确识别和脱敏。",
        "",
        "版本: v1.0",
        "创建日期: 2026年2月8日",
    ]

    for line in content:
        y_position -= line_height
        if y_position < 50:
            c.showPage()
            y_position = height - 50
        c.drawString(80, y_position, line)

    c.save()
    print(f"✓ 测试 PDF 已创建: {output_file}")
    return output_file

if __name__ == "__main__":
    create_test_pdf()
