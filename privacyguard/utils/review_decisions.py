"""Position-scoped review decisions; no global allowlist or original text."""
import hashlib
import json
import os
import math
from pathlib import Path

def geometry(hit):
    rect = hit.get("rect") if isinstance(hit, dict) else hit
    return [round(value, 4) for value in (rect.x(), rect.y(), rect.width(), rect.height())]


def page_fingerprint(page):
    scale = min(.25, math.sqrt(2000000 / max(1, page.rect.width * page.rect.height)))
    pix = page.get_pixmap(matrix=__import__("fitz").Matrix(scale, scale), annots=False)
    digest = hashlib.sha256(str((tuple(page.rect), tuple(page.cropbox), page.rotation)).encode())
    digest.update(pix.samples)
    for xref in page.get_contents():
        digest.update(page.parent.xref_stream(xref))
    # Visible pixels alone cannot bind invisible OCR text or full-resolution
    # image changes. Hash both text geometry and original image-block bytes.
    digest.update(json.dumps(page.get_text("rawdict", flags=0), sort_keys=True, ensure_ascii=True).encode())
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") == 1:
            digest.update(block.get("image") or b"")
            digest.update(block.get("mask") or b"")
    for widget in page.widgets():
        digest.update(repr((widget.field_name, widget.field_value, tuple(widget.rect))).encode("utf-8"))
    return digest.hexdigest()


def pdf_review_hits(entry, hits, fingerprint):
    for decision in entry.get("_review", []):
        decision["stale"] = decision.get("fingerprint") != fingerprint
    decisions = {tuple(d["geometry"]): d["state"] for d in entry.get("_review", [])
                 if d.get("fingerprint") == fingerprint}
    return [hit for hit in hits if decisions.get(tuple(geometry(hit))) != "excluded"]


def valid_pdf_decisions(items):
    if not isinstance(items, list):
        return []
    result = []
    for value in items[:100000]:
        if not isinstance(value, dict) or value.get("state") not in ("confirmed", "excluded"):
            continue
        bounds = value.get("geometry")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 4 or not all(
            isinstance(n, (int, float)) and math.isfinite(n) for n in bounds):
            continue
        if bounds[2] <= 0 or bounds[3] <= 0 or not isinstance(value.get("fingerprint"), str):
            continue
        result.append(dict(value, geometry=list(bounds)))
    return result


def word_match_key(match):
    digest = hashlib.sha256(str(match.get("text", "")).encode("utf-8")).hexdigest()
    return f'{match.get("start")}:{match.get("end")}:{digest}'


def word_review_hits(entry, hits):
    decisions = entry.get("_review", {})
    removed = entry.setdefault("_review_removed", {})
    for hit in hits:
        if decisions.get(word_match_key(hit)) == "excluded":
            removed[word_match_key(hit)] = hit
    return [hit for hit in hits if decisions.get(word_match_key(hit)) != "excluded"]


class WordReviewStore:
    """Only hashes/offsets/decisions are stored; no plaintext or mappings."""
    def __init__(self, source, base_dir):
        self.source = Path(source)
        key = hashlib.sha256(os.path.normcase(os.path.abspath(source)).encode()).hexdigest()[:24]
        self.path = Path(base_dir) / ("word-review-" + key + ".pgreview.json")

    def fingerprint(self):
        digest = hashlib.sha256()
        with self.source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def load(self):
        try:
            if self.path.stat().st_size > 1024 * 1024:
                return {}
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") != 1 or data.get("fingerprint") != self.fingerprint():
                return {}
            result = data.get("decisions", {})
            if not isinstance(result, dict) or len(result) > 100000:
                return {}
            return {key: value for key, value in result.items() if isinstance(key, str) and isinstance(value, dict)
                    and all(isinstance(k, str) and v in ("confirmed", "excluded") for k, v in value.items())}
        except (OSError, ValueError, TypeError):
            return {}

    def save(self, word_data):
        from .export_transaction import AtomicExport
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        decisions = {key: entry["_review"] for key, entry in word_data.items() if entry.get("_review")}
        data = {"version": 1, "fingerprint": self.fingerprint(), "decisions": decisions}
        with AtomicExport(self.path) as output:
            output.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            output.commit()

    def delete(self):
        self.path.unlink(missing_ok=True)
