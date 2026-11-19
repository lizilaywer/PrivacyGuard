"""Compare isolated OCR runtimes using the same synthetic input and models.

Run once normally and once with PYTHONPATH pointing to an isolated candidate.
The output contains synthetic OCR only, no user's files. Network is forbidden.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import socket
import statistics
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_ocr_geometry import sample
from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.ocr.model_paths import local_model_params


def evaluate(cases):
    engine = RapidOCREngine()
    outputs, times, recalled, targets = [], [], 0, 0
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("offline evaluation")):
        for index in range(cases):
            image, known = sample(index if index < cases//2 else index+24)
            started = time.perf_counter()
            results = engine.recognize(image)
            times.append(time.perf_counter()-started)
            recalled += sum(any(value in result.text for result in results) for value, _mask in known)
            targets += len(known)
            outputs.append([{"text": r.text, "box": r.box, "confidence": r.confidence} for r in results])
    return {"rapidocr": version("rapidocr"), "onnxruntime": version("onnxruntime"),
            "cases": cases, "targets": targets, "recognized_targets": recalled,
            "model_sha256": {Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in local_model_params().values()},
            "cold_ms": times[0]*1000, "warm_p50_ms": statistics.median(times[1:])*1000,
            "times_ms": [t*1000 for t in times], "outputs": outputs,
            "scope": "Synthetic runtime compatibility, not real-document accuracy certification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=int, default=16)
    args = parser.parse_args()
    result = evaluate(args.cases)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("outputs", "times_ms", "model_sha256")},ensure_ascii=False))
