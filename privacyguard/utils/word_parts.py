"""One Word content map for scanning, manual review, replacement and batch.

Edits touch text nodes only, retaining runs, styles, pictures and revisions.
Nested paragraphs (textboxes) are independent blocks. Existing body/cell keys
are retained so the ordinary dual preview and existing rules keep working.
"""
from dataclasses import dataclass, field
from collections import Counter

from lxml import etree
from docx.oxml.ns import qn

from .export_transaction import ExportValidationError
from .helpers_word_doc import iter_word_header_footer_paragraphs, iter_word_header_footer_cells

W_P = qn("w:p")
TEXT_TAGS = {qn("w:t"), qn("w:delText"), qn("w:instrText"), qn("a:t"), qn("m:t")}


@dataclass
class WordBlock:
    key: str
    label: str
    tokens: list
    kind: str = "xml"
    relationship: object = None
    part: object = None
    root: object = None

    @property
    def text(self):
        if self.relationship is not None:
            return self.relationship.target_ref
        return "".join((node.text or "") if node is not None else value for node, value in self.tokens)

    def replace(self, matches):
        text = self.text
        selected = []
        occupied = -1
        for match in sorted(matches, key=lambda m: (m["start"], -m["end"])):
            start, end = match["start"], match["end"]
            if not (0 <= start < end <= len(text)) or start < occupied:
                continue
            if match.get("text", text[start:end]) != text[start:end]:
                raise ExportValidationError("Word 内容已变化，请重新扫描后导出。")
            selected.append(match)
            occupied = end
        if self.relationship is not None:
            result = text
            for match in reversed(selected):
                result = result[:match["start"]] + match.get("replacement", "[已脱敏]") + result[match["end"]:]
            self.relationship._target = result
            return len(selected)
        ranges = []
        offset = 0
        for node, value in self.tokens:
            length = len(node.text or "") if node is not None else len(value)
            ranges.append((node, offset, offset + length))
            offset += length
        for match in reversed(selected):
            start, end = match["start"], match["end"]
            replacement = str(match.get("replacement", "[已脱敏]"))
            inserted = False
            for node, left, right in ranges:
                if end <= left or start >= right:
                    continue
                if node is None:
                    # Matching over paragraph separators is supported by
                    # replacing text either side, not restructuring the table.
                    continue
                old = node.text or ""
                a, b = max(0, start-left), min(right-left, end-left)
                node.text = old[:a] + (replacement if not inserted else "") + old[b:]
                node.set(qn("xml:space"), "preserve")
                inserted = True
            if not inserted:
                raise ExportValidationError("Word 区间没有可替换文字，导出已中止。")
        return len(selected)


def _paragraph_tokens(paragraph):
    tokens = []
    for node in paragraph.iter():
        if node.tag not in TEXT_TAGS | {qn("w:tab"), qn("w:br"), qn("w:cr")}:
            continue
        ancestor = node.getparent()
        while ancestor is not None and ancestor.tag != W_P:
            ancestor = ancestor.getparent()
        if ancestor is not paragraph:
            continue
        if node.tag in TEXT_TAGS and _hidden_node(node):
            continue
        if node.tag in TEXT_TAGS:
            tokens.append((node, ""))
        else:
            tokens.append((None, "\t" if node.tag == qn("w:tab") else "\n"))
    return tokens


def _hidden_node(node):
    if node.tag in (qn("w:delText"), qn("w:instrText")):
        return True
    parent = node.getparent()
    while parent is not None and parent.tag != W_P:
        if parent.tag == qn("w:del"):
            return True
        if parent.tag == qn("w:r"):
            props = parent.find(qn("w:rPr"))
            hidden = props.find(qn("w:vanish")) if props is not None else None
            if hidden is not None and hidden.get(qn("w:val"), "true") not in ("false", "0", "off"):
                return True
        parent = parent.getparent()
    return False


@dataclass
class WordContent:
    blocks: list = field(default_factory=list)
    roots: list = field(default_factory=list)
    risks: Counter = field(default_factory=Counter)

    def commit(self):
        for part, root in self.roots:
            part._blob = etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)


def map_word_content(doc):
    content = WordContent()
    seen = set()
    def paragraph(key, element, label, kind):
        if element in seen:
            return
        seen.add(element)
        content.blocks.append(WordBlock(key, label, _paragraph_tokens(element), kind))
    def cell(key, cell_obj, label):
        tokens = []
        for idx, para in enumerate(cell_obj.paragraphs):
            if para._p in seen:
                continue
            if idx:
                tokens.append((None, "\n"))
            seen.add(para._p)
            tokens.extend(_paragraph_tokens(para._p))
        if tokens:
            content.blocks.append(WordBlock(key, label, tokens, "table_cell"))
    for idx, para in enumerate(doc.paragraphs):
        paragraph(f"paragraph_{idx}", para._p, f"正文段落 {idx+1}", "paragraph")
    seen_cells = set()
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, item in enumerate(row.cells):
                if item._tc not in seen_cells:
                    seen_cells.add(item._tc)
                    cell(f"table_{ti}_cell_{ri}_{ci}", item, f"表格 {ti+1}/{ri+1}/{ci+1}")
    for key, para in iter_word_header_footer_paragraphs(doc):
        paragraph(key, para._p, "页眉/页脚", "header_footer_paragraph")
    for key, item in iter_word_header_footer_cells(doc):
        cell(key, item, "页眉/页脚表格")

    total_bytes = 0
    for part in doc.part.package.parts:
        name = str(part.partname)
        if any(marker in name.lower() for marker in ("/embeddings/", "vbaproject", "/activex/")):
            content.risks["嵌入对象/宏/控件"] += 1
        if name.startswith("/_xmlsignatures/"):
            content.risks["数字签名（修改后可能失效）"] += 1
        for rel in part.rels.values():
            if rel.is_external:
                if rel.reltype.endswith("/hyperlink"):
                    content.blocks.append(WordBlock(f"rel:{name}:{rel.rId}", "超链接目标", [], "relationship", relationship=rel))
                else:
                    content.risks["外部资源关系（未访问）"] += 1
        if not name.endswith(".xml") or not name.startswith(("/word/", "/docProps/", "/customXml/")):
            continue
        total_bytes += len(part.blob)
        if total_bytes > 32 * 1024 * 1024:
            raise ExportValidationError("Word XML 超出处理上限，请拆分文件。")
        root = getattr(part, "_element", None)
        if root is None:
            parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
            root = etree.fromstring(part.blob, parser)
            if root.getroottree().docinfo.doctype:
                raise ExportValidationError("Word XML 含不支持的 DTD，已停止处理。")
            content.roots.append((part, root))
        if root.getroottree().docinfo.doctype:
            raise ExportValidationError("Word XML 含不支持的 DTD，已停止处理。")
        paragraphs = list(root.iter(W_P))
        for idx, para in enumerate(paragraphs):
            paragraph(f"xml:{name}:p{idx}", para, name.rsplit("/", 1)[-1] + f" 段落 {idx+1}", "xml")
            hidden = []
            for node in para.iter():
                if node.tag not in TEXT_TAGS or not _hidden_node(node):
                    continue
                nearest = node.getparent()
                while nearest is not None and nearest.tag != W_P:
                    nearest = nearest.getparent()
                if nearest is para:
                    hidden.append((node, ""))
            if hidden:
                content.blocks.append(WordBlock(f"xml:{name}:hidden{idx}", "隐藏/修订/字段文字", hidden, "hidden"))
        # Core/custom properties and DrawingML chart labels/alt descriptions.
        for idx, node in enumerate(root.iter()):
            if not isinstance(node.tag, str):
                continue
            if node.tag == qn("w:altChunk"):
                content.risks["外来内容块"] += 1
            if node.tag == qn("w:dataBinding"):
                content.risks["自定义 XML 数据绑定"] += 1
            if node.tag in (qn("w:ins"), qn("w:del")):
                content.risks["修订（已纳入文字扫描，保留修订结构）"] += 1
            ancestor = node
            while ancestor is not None and ancestor.tag != W_P:
                ancestor = ancestor.getparent()
            if ancestor is None and len(node) == 0 and (node.text or "").strip():
                local = etree.QName(node).localname
                if name.startswith(("/docProps/", "/customXml/")) or local in ("t", "delText", "instrText"):
                    content.blocks.append(WordBlock(f"xml:{name}:t{idx}", name.rsplit("/",1)[-1], [(node, "")]))
            # Descriptive attributes (including author names) must not be
            # confused with schema/relationship identifiers.
            for attribute in ("descr", "title", qn("w:author"), qn("w:initials")):
                if node.get(attribute):
                    content.blocks.append(_attribute_block(f"xml:{name}:a{idx}:{attribute}", node, attribute))
    if len(content.blocks) > 100000:
        raise ExportValidationError("Word 内容块过多，请拆分文件。")
    return content


def _attribute_block(key, node, attribute):
    class AttributeBlock(WordBlock):
        @property
        def text(self):
            return node.get(attribute, "")
        def replace(self, matches):
            from .helpers_word_rules import apply_rule_matches_to_text
            node.set(attribute, apply_rule_matches_to_text(self.text, matches))
            return len(matches)
    return AttributeBlock(key, "属性/替代说明", [])


def build_word_data(doc):
    content = map_word_content(doc)
    return {block.key: {"type": block.kind, "label": block.label, "text": block.text,
                        "ocr": [], "manual": []} for block in content.blocks}


def apply_word_data(doc, data, rules, replacement, custom_keyword_rules=None):
    from .helpers_word_rules import merge_word_matches_with_priority
    from .helpers_word_preview import resolve_word_ocr_replacements
    content = map_word_content(doc)
    known = {block.key: block for block in content.blocks}
    for key, entry in data.items():
        if key.startswith("__") or not isinstance(entry, dict):
            continue
        block = known.get(key)
        if block is None or block.text != entry.get("text", ""):
            raise ExportValidationError("Word 内容与扫描清单不一致，请重新打开并扫描。")
        matches = merge_word_matches_with_priority(block.text, rules, replacement,
                    manual_matches=entry.get("manual", []),
                    ocr_matches=resolve_word_ocr_replacements(entry.get("ocr", []), custom_keyword_rules, replacement))
        block.replace(matches)
    content.commit()
    return content.risks


def apply_word_rules(doc, rules, replacement):
    from .helpers_word_rules import build_word_rule_matches
    content = map_word_content(doc)
    counts = Counter()
    total = 0
    for block in content.blocks:
        matches = build_word_rule_matches(block.text, rules, replacement)
        total += block.replace(matches)
        counts.update(m["rule_index"] for m in matches)
    content.commit()
    return {"total_replacements": total, "rule_counts": [{"rule_index": i, "count": n} for i, n in sorted(counts.items())],
            "coverage_notes": dict(content.risks)}
