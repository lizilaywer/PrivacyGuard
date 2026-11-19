"""Shared Word XML scan/write contract across otherwise hidden content."""
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.opc.constants import RELATIONSHIP_TYPE as RT

from privacyguard.utils.word_parts import build_word_data, apply_word_data, apply_word_rules, map_word_content
from privacyguard.utils.export_transaction import save_verified_docx, ExportValidationError
from privacyguard.utils.helpers_word_rules import build_word_rule_matches

SECRET = "CANARY_SECRET"
RULES = [{"enabled": True, "mode": "exact", "find": SECRET, "replace": "[REDACTED]"}]


class WordPartsTests(unittest.TestCase):
    def doc(self):
        doc = Document()
        p = doc.add_paragraph()
        p.add_run("KEEP " + SECRET[:6]).bold = True
        p.add_run(SECRET[6:] + " KEEP").italic = True
        hyperlink = OxmlElement("w:hyperlink")
        rid = doc.part.relate_to("mailto:" + SECRET + "@example.invalid", RT.HYPERLINK, is_external=True)
        hyperlink.set(qn("r:id"), rid)
        run = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = SECRET
        run.append(t)
        hyperlink.append(run)
        p._p.append(hyperlink)
        cell = doc.add_table(rows=1, cols=1).cell(0, 0)
        cell.text = SECRET
        cell.add_table(rows=1, cols=1).cell(0, 0).text = SECRET
        doc.sections[0].header.paragraphs[0].text = SECRET
        doc.core_properties.author = SECRET
        footnotes = Part(PackURI("/word/footnotes.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
            ('<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
             '<w:footnote w:id="1"><w:p><w:r><w:t>'+SECRET+'</w:t></w:r></w:p></w:footnote></w:footnotes>').encode(), doc.part.package)
        doc.part.relate_to(footnotes, RT.FOOTNOTES)
        deleted = OxmlElement("w:del")
        deleted.set(qn("w:author"), SECRET)
        r = OxmlElement("w:r")
        dt = OxmlElement("w:delText")
        dt.text = SECRET
        r.append(dt)
        deleted.append(r)
        doc.add_paragraph()._p.append(deleted)
        return doc

    def test_shared_map_covers_hyperlinks_nested_tables_properties_and_footnotes(self):
        doc = self.doc()
        data = build_word_data(doc)
        self.assertIn("paragraph_0", data)
        self.assertTrue(any(k.startswith("rel:") for k in data))
        self.assertTrue(any("footnotes" in k for k in data))
        for entry in data.values():
            entry["ocr"] = build_word_rule_matches(entry["text"], RULES)
        apply_word_data(doc, data, [], "[DEFAULT]")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.docx"
            save_verified_docx(doc, path)
            with ZipFile(path) as package:
                for name in package.namelist():
                    if name.endswith((".xml", ".rels")):
                        self.assertNotIn(SECRET.encode(), package.read(name), name)
            reopened = Document(path)
            self.assertTrue(reopened.paragraphs[0].runs[0].bold)
            self.assertTrue(reopened.paragraphs[0].runs[1].italic)
            self.assertIn("KEEP", reopened.paragraphs[0].text)

    def test_batch_same_map_no_duplicate_merged_cells(self):
        doc = Document()
        table = doc.add_table(rows=1, cols=2)
        table.cell(0, 0).merge(table.cell(0, 1)).text = SECRET
        result = apply_word_rules(doc, RULES, "[DEFAULT]")
        self.assertEqual(result["total_replacements"], 1)
        self.assertIn("[REDACTED]", table.cell(0, 0).text)

    def test_stale_scan_cannot_write_wrong_offsets(self):
        doc = Document()
        p = doc.add_paragraph(SECRET)
        data = build_word_data(doc)
        p.text = "CHANGED"
        with self.assertRaises(ExportValidationError):
            apply_word_data(doc, data, RULES, "[DEFAULT]")

    def test_two_matches_in_single_node_preserve_order_and_suffix(self):
        doc = Document()
        doc.add_paragraph(SECRET + " middle " + SECRET + " suffix")
        apply_word_rules(doc, RULES, "[DEFAULT]")
        self.assertEqual(doc.paragraphs[0].text, "[REDACTED] middle [REDACTED] suffix")

    def test_textbox_is_separate_and_no_double_count(self):
        doc = Document()
        p = doc.add_paragraph(SECRET)
        box = OxmlElement("w:txbxContent")
        inner = OxmlElement("w:p")
        run = OxmlElement("w:r")
        text = OxmlElement("w:t")
        text.text = SECRET
        run.append(text)
        inner.append(run)
        box.append(inner)
        p._p.append(box)
        matches = [b.text for b in map_word_content(doc).blocks if SECRET in b.text]
        self.assertEqual(len(matches), 2)
        self.assertEqual(apply_word_rules(doc, RULES, "[DEFAULT]")["total_replacements"], 2)
