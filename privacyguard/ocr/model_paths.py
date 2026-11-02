"""Resolve the pinned offline OCR models without invoking any downloader."""

from pathlib import Path


def local_model_params():
    import rapidocr

    root = Path(rapidocr.__file__).resolve().parent / "models"
    models = {"Det": "PP-OCRv6_det_small.onnx",
              "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
              "Rec": "PP-OCRv6_rec_small.onnx"}
    params = {}
    for task, name in models.items():
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"Bundled OCR model missing: {name}")
        params[f"{task}.model_path"] = str(path)
    return params
