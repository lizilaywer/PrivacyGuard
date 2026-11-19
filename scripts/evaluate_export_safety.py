"""Generate and validate a public synthetic PDF export corpus (no private data).

120 independent files / 300 pages / 1200 known targets by default. These are
synthetic variations, not 120 independent real-world document sources. The
checks exercise saved files and are not a general OCR-accuracy benchmark.
"""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw
from PyQt6.QtCore import QRectF

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacyguard.utils.export_transaction import save_verified_pdf


def run(root, count):
    root.mkdir(parents=True,exist_ok=True)
    summary={'files':count,'pages':0,'targets':0,'source_checks':0,'reopened':0,
             'mode':'Synthetic PDF export verification; not an OCR benchmark','families':{}}
    for index in range(count):
        family=['text','image','mixed'][index%3]
        summary['families'][family]=summary['families'].get(family,0)+1
        with fitz.open() as source:
            data={}
            pages=2+index%2
            for pno in range(pages):
                page=source.new_page(width=320,height=240)
                hits=[]
                if family=='text':
                    for n in range(4):
                        word=f'PRIVATE{n}'
                        page.insert_text((40,45+n*40),word+' PUBLIC')
                        r=page.search_for(word)[0]
                        hits.append({'rect':QRectF(r.x0,r.y0,r.width,r.height),'replace_text':''})
                else:
                    image=Image.new('RGB',(320,240),'white')
                    draw=ImageDraw.Draw(image)
                    for n in range(4):
                        draw.text((40,35+n*40),f'PRIVATE{n}',fill='black')
                        hits.append({'rect':QRectF(36,30+n*40,78,25),'replace_text':''})
                    buffer=io.BytesIO()
                    image.save(buffer,format='PNG')
                    page.insert_image(page.rect,stream=buffer.getvalue())
                    if family=='mixed':
                        page.insert_text((150,22),'PUBLIC TEXT')
                if index%4:
                    page.set_rotation((index%4)*90)
                    for hit in hits:
                        r=hit['rect']
                        disp=fitz.Rect(r.x(),r.y(),r.right(),r.bottom())*page.rotation_matrix
                        hit['rect']=QRectF(disp.x0,disp.y0,disp.width,disp.height)
                data[pno]={'ocr':hits,'manual':[]}
            source.set_toc([[1,'PUBLIC BOOKMARK',1]])
            source_text=[p.get_text() for p in source]
            source_images=[hashlib.sha256(p.get_pixmap().samples).hexdigest() for p in source]
            original=source.tobytes()
            with fitz.open(stream=original,filetype='pdf') as edited:
                for pno,page in enumerate(edited):
                    for hit in data[pno]['ocr']:
                        q=hit['rect']
                        r=fitz.Rect(q.x(),q.y(),q.right(),q.bottom())
                        if page.rotation:
                            r=(r*page.derotation_matrix).normalize()
                        page.add_redact_annot(r,fill=(0,0,0))
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
                kwargs={'garbage':2,'deflate':True,'clean':True}
                if index%5==0:
                    kwargs.update(encryption=fitz.PDF_ENCRYPT_AES_256,user_pw='open-test',owner_pw='owner-test')
                path=root/f'case-{index:03}.pdf'
                assert save_verified_pdf(edited,path,kwargs,data)==pages*4
                with fitz.open(path) as saved:
                    if saved.needs_pass:
                        assert saved.authenticate('open-test')>0
                    assert len(saved)==pages and saved.get_toc()==[[1,'PUBLIC BOOKMARK',1]]
                    for pno,page in enumerate(saved):
                        assert 'PRIVATE' not in page.get_text()
                        if family=='text':
                            assert 'PUBLIC' in page.get_text()
                        elif family=='mixed':
                            assert 'PUBLIC TEXT' in page.get_text()
                        # Rendering checks that marked image areas are opaque.
                        for hit in data[pno]['ocr']:
                            q=hit['rect']
                            clip=fitz.Rect(q.x()+2,q.y()+2,q.right()-2,q.bottom()-2)
                            pix=page.get_pixmap(clip=clip,alpha=False)
                            assert pix.samples and max(pix.samples)<=2
                    summary['reopened']+=1
            # The source still contains original text/image data, unchanged.
            assert [p.get_text() for p in source]==source_text
            assert [hashlib.sha256(p.get_pixmap().samples).hexdigest() for p in source]==source_images
            summary['source_checks']+=1
            summary['pages']+=pages
            summary['targets']+=pages*4
        if index%20==0:
            print(f'Validated {index+1}/{count} synthetic files',flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=120)
    parser.add_argument('--root',type=Path,default=Path('tests/output/export-upgrade'))
    args=parser.parse_args()
    report=run(args.root,args.count)
    (args.root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
