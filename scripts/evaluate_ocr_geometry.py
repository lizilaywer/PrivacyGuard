"""Offline synthetic comparison of old/new OCR geometry, without changing config.

Uses public fictional fields only. Generated image variants share a case family;
they must not be split across train/holdout groups in future model tuning.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.workers.ocr_worker import OCRWorker


def sample(index):
    font_path = "C:/Windows/Fonts/" + ("simsun.ttc" if index % 2 else "msyh.ttc")
    font = ImageFont.truetype(font_path, [24, 28, 32, 36][index % 4])
    image = Image.new("RGB", (1160, 220), "white")
    draw = ImageDraw.Draw(image)
    targets = []
    rows = [[("申请人：", False), ("张三", True), ("；电话：", False), ("13812345678", True)],
            [("证件：", False), ("110101199001011234", True), ("；金额：", False), ("1250.50", True), ("元。", False)]]
    if index >= 24:
        font_path = "C:/Windows/Fonts/" + ("simhei.ttf" if index % 3 == 0 else "msyh.ttc")
        font = ImageFont.truetype(font_path, [20, 26, 30, 34, 42][index % 5])
        name = ["李四", "王小明", "欧阳明"][index % 3]
        rows = [[("原告：",False),(name,True),("；联系方式：",False),("13987654321",True)],
                [("编号：",False),("HT-2026-001",True),("；转账：",False),("8650.25",True),("元。",False)]]
    for row_number, row in enumerate(rows):
        x, y = 25.0 + index % 7, 25 + row_number * 85
        for value, sensitive in row:
            draw.text((x, y), value, font=font, fill="black")
            if sensitive:
                mask = Image.new("L", image.size, 0)
                ImageDraw.Draw(mask).text((x, y), value, font=font, fill=255)
                targets.append((value, np.asarray(mask) > 100))
            x += draw.textlength(value, font=font)
    if index % 3 == 1:
        image = image.filter(ImageFilter.GaussianBlur(.35))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR), targets


def coverage(rect, mask):
    height, width = mask.shape
    x0, y0 = max(0, math.floor(rect.x())), max(0, math.floor(rect.y()))
    x1, y1 = min(width, math.ceil(rect.right())), min(height, math.ceil(rect.bottom()))
    return int(mask[y0:y1, x0:x1].sum()) / max(1, int(mask.sum()))


def run(cases):
    engine = RapidOCREngine(enable_char_boxes=True)
    worker = OCRWorker("unused.pdf", [], False, "", 1, 0, 0)
    measurements = []
    regression = []
    recognized = 0
    used = 0
    for index in range(cases):
        image, targets = sample(index)
        normal_ink = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 155
        for _value, target_mask in targets:
            normal_ink &= ~target_mask
        output = engine.recognize(image)
        for target_index, (value, mask) in enumerate(targets):
            matches = [(r, r.text.find(value)) for r in output if value in r.text]
            if not matches:
                continue
            recognized += 1
            r, start = matches[0]
            span = start, start + len(value)
            old = worker.calculate_sub_rect(r.box, r.text, span, img_region=image)
            new = worker.calculate_sub_rect(r.box, r.text, span, img_region=image, chars=r.chars)
            if old is None or new is None:
                raise AssertionError("Synthetic target produced no mask")
            old_cover, new_cover = coverage(old, mask), coverage(new, mask)
            changed = old != new
            used += changed
            def collateral(rect):
                y0, y1 = max(0,math.floor(rect.y())), min(image.shape[0],math.ceil(rect.bottom()))
                x0, x1 = max(0,math.floor(rect.x())), min(image.shape[1],math.ceil(rect.right()))
                return int(normal_ink[y0:y1,x0:x1].sum())
            item = {"case": index, "target_type": target_index,
                    "old_coverage":old_cover,"new_coverage":new_cover,"changed":changed,
                    "old_area":old.width()*old.height(),"new_area":new.width()*new.height(),
                    "old_non_sensitive_ink":collateral(old),"new_non_sensitive_ink":collateral(new)}
            measurements.append(item)
            if new_cover + 1e-9 < old_cover:
                regression.append(item)
        if index % 10 == 0:
            print(f"Compared {index+1}/{cases} synthetic pages", flush=True)
    timings = {False:[],True:[]}
    image, _ = sample(0)
    for _ in range(6):
        for enabled in (False, True):
            engine.enable_char_boxes = enabled
            t = time.perf_counter()
            engine.recognize(image)
            timings[enabled].append((time.perf_counter()-t)*1000)
    old_collateral = sum(m['old_non_sensitive_ink'] for m in measurements)
    new_collateral = sum(m['new_non_sensitive_ink'] for m in measurements)
    incomplete = sum(m['new_coverage'] < 1 for m in measurements)
    return {"scope":"Synthetic geometry evaluation, not a guarantee for real documents",
            "candidate_passed":not regression and not incomplete and new_collateral <= old_collateral
            and recognized == cases * 4,
            "cases":cases,"targets":cases*4,"recognized":recognized,"precise_used":used,
            "new_coverage_regressions":len(regression),"regressions":regression,
            "old_mean_coverage":statistics.mean(m['old_coverage'] for m in measurements),
            "new_mean_coverage":statistics.mean(m['new_coverage'] for m in measurements),
            "new_incomplete_targets":sum(m['new_coverage'] < 1 for m in measurements),
            "old_non_sensitive_ink":sum(m['old_non_sensitive_ink'] for m in measurements),
            "new_non_sensitive_ink":sum(m['new_non_sensitive_ink'] for m in measurements),
            "median_area_ratio":statistics.median(m['new_area']/m['old_area'] for m in measurements),
            "median_ms":{str(k):statistics.median(v) for k,v in timings.items()},
            "input_family_sha256":hashlib.sha256(image.tobytes()).hexdigest(),
            "measurements":measurements}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=int, default=24)
    parser.add_argument('--output', type=Path, default=Path('logs/ocr_geometry_evaluation.json'))
    args = parser.parse_args()
    report = run(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('measurements','regressions')},indent=2))
    raise SystemExit(not report['candidate_passed'])
