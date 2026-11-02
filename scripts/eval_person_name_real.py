# -*- coding: utf-8 -*-
"""cp_person_name 阶段2 实测脚本：用真实诉讼卷宗评估称谓人名识别（不进 CI）。

用法（项目根目录）：
    # 默认卷宗全卷
    .\\venv_win\\Scripts\\python.exe scripts\\eval_person_name_real.py

    # 前 30 页抽样（1-based，从第 1 页起）
    .\\venv_win\\Scripts\\python.exe scripts\\eval_person_name_real.py 30

    # 指定页范围 50-80（1-based 闭区间）
    .\\venv_win\\Scripts\\python.exe scripts\\eval_person_name_real.py 50 80

    # 指定 PDF（环境变量，默认路径找不到/被替换时用）
    $env:PG_EVAL_PDF="C:\\path\\to\\卷宗.pdf"
    .\\venv_win\\Scripts\\python.exe scripts\\eval_person_name_real.py 30

输出：
    scripts/person_name_eval_report.txt —— 每页命中明细（人名 + 上下文）
    stdout —— 汇总（去重人名清单 + 各自出现页码），供人工抽检统计准确率
"""
import os
import sys

import fitz

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PDF = r"C:\Users\49144\Downloads\77777777777777111222333.pdf"
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "person_name_eval_report.txt")

sys.path.insert(0, PROJECT_ROOT)

from privacyguard.ocr.person_name import (  # noqa: E402
    build_person_name_pattern, DEFAULT_TITLES,
    find_person_names_by_pattern,
)


def get_ocr_engine():
    from privacyguard.ocr.rapidocr import RapidOCREngine
    engine = RapidOCREngine()
    if not engine.is_available():
        print("[FATAL] RapidOCR 引擎不可用：", engine.get_last_error())
        sys.exit(1)
    return engine


def ocr_page_lines(engine, page, scale=1.5):
    """渲染整页并 OCR，返回行文本列表。"""
    import numpy as np
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    bgr = arr[:, :, :3][:, :, ::-1]
    results = engine.recognize(bgr)
    lines = []
    for r in results or []:
        text = getattr(r, "text", "")
        if text:
            lines.append(text)
    return lines


def main():
    pdf_path = os.environ.get("PG_EVAL_PDF", "")
    if not pdf_path:
        # 默认路径优先级：项目根卷宗 → Downloads 历史样本
        local = os.path.join(PROJECT_ROOT, "诉讼文书卷.pdf")
        pdf_path = local if os.path.exists(local) else DEFAULT_PDF
    if not os.path.exists(pdf_path):
        print(f"[FATAL] 样本不存在: {pdf_path}")
        # 列出 Downloads 里的 PDF 候选帮助定位
        dl = os.path.dirname(DEFAULT_PDF)
        try:
            cands = [f for f in os.listdir(dl) if f.lower().endswith(".pdf")]
            if cands:
                print("Downloads 下的 PDF 候选（用 $env:PG_EVAL_PDF 指定）：")
                for f in cands[:15]:
                    print(f"    {os.path.join(dl, f)}")
        except OSError:
            pass
        sys.exit(1)

    # 页范围参数：无参=全卷；单参 N=第 1..N 页；双参 A B=第 A..B 页
    start, end = 1, None
    if len(sys.argv) == 2:
        end = int(sys.argv[1])
    elif len(sys.argv) >= 3:
        start, end = int(sys.argv[1]), int(sys.argv[2])

    engine = get_ocr_engine()
    pattern = build_person_name_pattern(DEFAULT_TITLES)

    doc = fitz.open(pdf_path)
    total = len(doc)
    start = max(1, min(start, total))
    end = min(end or total, total)
    if start > end:
        print(f"[FATAL] 页范围无效：第 {start}-{end} 页（共 {total} 页）")
        sys.exit(1)
    print(f"卷宗: {os.path.basename(pdf_path)} 共 {total} 页")
    print(f"评估范围: 第 {start}-{end} 页（OCR 渲染 1.5x，耐心等待）\n")

    # name -> {pages: [], contexts: []}
    found = {}
    report_lines = []

    for pno in range(start - 1, end):
        page = doc[pno]
        page_no = pno + 1
        try:
            lines = ocr_page_lines(engine, page)
        except Exception as e:
            report_lines.append(f"[第{page_no}页] OCR 失败: {type(e).__name__}")
            continue

        page_hits = []
        for text in lines:
            for name, s, e_off in find_person_names_by_pattern(text, pattern):
                ctx = text[max(0, s - 8):min(len(text), e_off + 8)]
                page_hits.append((name, ctx))
                entry = found.setdefault(name, {"pages": set(), "contexts": []})
                entry["pages"].add(page_no)
                if len(entry["contexts"]) < 3:
                    entry["contexts"].append(f"…{ctx}…")

        if page_hits:
            report_lines.append(f"[第{page_no}页]")
            for name, ctx in page_hits:
                report_lines.append(f"    {name}  ←  …{ctx}…")

        if page_no % 20 == 0:
            print(f"  已处理 {page_no}/{end} 页，累计发现 {len(found)} 个不同人名…")

    doc.close()

    # 报告落盘
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) if report_lines else "(无命中)")

    # 汇总输出
    print("\n" + "=" * 60)
    print(f"发现 {len(found)} 个不同人名（按出现页数排序）：")
    print("=" * 60)
    for name, entry in sorted(found.items(), key=lambda kv: -len(kv[1]["pages"])):
        pages = sorted(entry["pages"])
        pages_str = ",".join(str(p) for p in pages[:12]) + (
            f"…共{len(pages)}页" if len(pages) > 12 else "")
        print(f"\n  {name}  ({pages_str})")
        for ctx in entry["contexts"]:
            print(f"      {ctx}")

    print(f"\n明细报告: {REPORT_PATH}")
    print("\n请人工抽检以上清单：误检（不是人名的）→ 需扩充停用词表；")
    print("翻看原卷对应页找漏检（称谓后有名字但没识别的）→ 告知 AI 样本继续调优。")


if __name__ == "__main__":
    main()
