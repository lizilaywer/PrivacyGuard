"""Create fictional documents for screenshots; never use client documents."""
from pathlib import Path

import fitz
from docx import Document
from docx.shared import Pt


def create_samples():
    root = Path(__file__).resolve().parents[1] / "tests/output/showcase"
    root.mkdir(parents=True, exist_ok=True)
    lines = [
        "项目协作备忘录 · 演示文档",
        "本文件全部内容为虚构，仅供软件功能展示。",
        "一、基本信息",
        "委托方：示例甲    协作方：示例乙",
        "联系电话：13800000000",
        "电子邮箱：demo@example.invalid",
        "测试服务器：192.0.2.10",
        "二、资料使用约定",
        "对外分享资料前，请先识别并处理其中的敏感信息。",
        "通过智能扫描发现候选项，再使用手动框选补充检查。",
        "导出后重新打开文件，核对正文、书签与文件属性。",
        "三、工作流程",
        "导入文档 → 扫描与标记 → 人工复核 → 导出结果",
        "演示数据不对应真实自然人、公司或案件。",
    ]
    with fitz.open() as pdf:
        for page_no in range(3):
            page = pdf.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(38, 35, 557, 100), color=None, fill=(0.93, 0.96, 1))
            for idx, line in enumerate(lines):
                page.insert_text((52, 68 + idx * 43), line, fontname="china-s",
                                 fontsize=17 if idx == 0 else 12, color=(0.10, 0.17, 0.28))
            page.insert_text((52, 798), f"PrivacyGuard / FICTIONAL DEMO / {page_no + 1}", fontsize=9)
        pdf.set_toc([[1, "演示文档 · 基本信息", 1], [1, "演示文档 · 工作流程", 2]])
        pdf.save(root / "PrivacyGuard-Demo.pdf")
    doc = Document()
    doc.styles["Normal"].font.size = Pt(12)
    for idx, line in enumerate(lines):
        if idx == 0:
            doc.add_heading(line, 0)
        elif line.startswith(("一、", "二、", "三、")):
            doc.add_heading(line, 1)
        else:
            doc.add_paragraph(line)
    doc.core_properties.author = "PrivacyGuard demo"
    doc.core_properties.last_modified_by = "PrivacyGuard demo"
    doc.save(root / "PrivacyGuard-Demo.docx")
    print("Created fictional PDF and DOCX in tests/output/showcase")


if __name__ == "__main__":
    create_samples()
