"""Open synthetic edited DOCX in an independent office implementation.

Requires an explicitly supplied LibreOffice binary. Uses an isolated profile,
only generated files, and never touches the user's Office settings/documents.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

import fitz
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacyguard.utils.word_parts import apply_word_rules
from privacyguard.utils.export_transaction import save_verified_docx

CANARY = "CANARYX"


def fixture():
    doc = Document()
    para = doc.add_paragraph()
    para.add_run("KEEP_VISIBLE ").bold = True
    para.add_run(CANARY).italic = True
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), doc.part.relate_to("mailto:"+CANARY+"@example.invalid", RT.HYPERLINK, is_external=True))
    run, text = OxmlElement("w:r"), OxmlElement("w:t")
    text.text = " "+CANARY
    run.append(text); link.append(run); para._p.append(link)
    cell = doc.add_table(rows=1, cols=1).cell(0,0)
    cell.text = CANARY
    cell.add_table(rows=1, cols=1).cell(0,0).text = CANARY
    doc.sections[0].header.paragraphs[0].text = "HEADER "+CANARY
    doc.sections[0].footer.paragraphs[0].text = "FOOTER KEEP_VISIBLE"
    doc.core_properties.author = CANARY
    note = Part(PackURI('/word/footnotes.xml'),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml',
                ('<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                 '<w:footnote w:id="1"><w:p><w:r><w:t>'+CANARY+'</w:t></w:r></w:p></w:footnote></w:footnotes>').encode(), doc.part.package)
    doc.part.relate_to(note, RT.FOOTNOTES)
    reference = OxmlElement('w:footnoteReference'); reference.set(qn('w:id'),'1')
    note_run = OxmlElement('w:r'); note_run.append(reference); para._p.append(note_run)
    hidden = OxmlElement('w:r')
    props = OxmlElement('w:rPr'); props.append(OxmlElement('w:vanish')); hidden.append(props)
    node = OxmlElement('w:t'); node.text=CANARY; hidden.append(node); para._p.append(hidden)
    return doc


def verify(soffice):
    version = subprocess.check_output([soffice,'--version'], timeout=30, text=True).strip()
    with tempfile.TemporaryDirectory(prefix='pg_office_interop_') as folder:
        root = Path(folder)
        before, after = root/'before.docx', root/'after.docx'
        doc = fixture(); doc.save(before)
        original = hashlib.sha256(before.read_bytes()).hexdigest()
        loaded = Document(before)
        apply_word_rules(loaded, [{'enabled':True,'mode':'exact','find':CANARY,'replace':'REMOVED'}], 'REMOVED')
        save_verified_docx(loaded, after, before)
        with ZipFile(after) as package:
            for name in package.namelist():
                if name.endswith(('.xml','.rels')) and CANARY.encode() in package.read(name):
                    raise AssertionError('Canary remains in edited package')
        pdfs = []
        for source in (before,after):
            output = root/source.stem; output.mkdir()
            profile = root/('profile-'+source.stem)
            result = subprocess.run([soffice,'-env:UserInstallation='+profile.as_uri(), '--headless', '--convert-to','pdf',
                                     '--outdir',str(output),str(source)], capture_output=True, timeout=120)
            path = output/(source.stem+'.pdf')
            if result.returncode or not path.is_file():
                raise AssertionError('Independent Office reopen/conversion failed')
            pdfs.append(path)
        with fitz.open(pdfs[0]) as baseline, fitz.open(pdfs[1]) as edited:
            if len(baseline) != len(edited):
                raise AssertionError('Page count changed in fixed synthetic fixture')
            text = ''.join(page.get_text() for page in edited)
            if CANARY in text or 'KEEP_VISIBLE' not in text or 'REMOVED' not in text:
                raise AssertionError('Independent Office output does not match replacement intent')
            if CANARY in repr([page.get_links() for page in edited]):
                raise AssertionError('Hyperlink target retained a canary')
        if hashlib.sha256(before.read_bytes()).hexdigest() != original:
            raise AssertionError('Source fixture changed')
        return {'office':version,'status':'passed','scope':'Synthetic body, nested table, hyperlink, header/footer, footnote, hidden text and properties',
                'source_unchanged':True,'same_page_count':True,'xml_relationship_canaries_removed':True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--soffice', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.soffice)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
