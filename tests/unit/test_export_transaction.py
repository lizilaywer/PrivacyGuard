"""Adversarial saved-file checks; never trust a black rectangle alone."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from PyQt6.QtCore import QRectF

from privacyguard.utils.document_source import SourceRevision
from privacyguard.utils.export_transaction import AtomicExport, ExportValidationError, save_verified_pdf, save_verified_docx
from privacyguard.utils.export_validation import verify_pdf_export, verify_docx_export


class TestAtomicExport(unittest.TestCase):
    def test_protects_original_and_decrypted_working_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'encrypted.docx'
            working = Path(directory)/'decrypted.docx'
            original.write_bytes(b'ENCRYPTED_ORIGINAL')
            working.write_bytes(b'DECRYPTED_WORKING')
            for target in (original, working):
                with self.assertRaises(ExportValidationError):
                    with AtomicExport(target, [original, working]):
                        self.fail('source must not be opened for writing')
            self.assertEqual(original.read_bytes(), b'ENCRYPTED_ORIGINAL')
            self.assertEqual(working.read_bytes(), b'DECRYPTED_WORKING')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.destination = self.root / 'out.pdf'
        self.destination.write_bytes(b'PREVIOUS_GOOD_FILE')

    def test_exception_preserves_target_and_removes_temp(self):
        with self.assertRaises(ValueError):
            with AtomicExport(self.destination) as export:
                export.path.write_bytes(b'BAD_OUTPUT')
                raise ValueError('synthetic')
        self.assertEqual(self.destination.read_bytes(), b'PREVIOUS_GOOD_FILE')
        self.assertEqual(list(self.root.glob('.pg-export-*')), [])

    def test_replace_failure_preserves_target(self):
        with patch('os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                with AtomicExport(self.destination) as export:
                    export.path.write_bytes(b'new')
                    export.commit()
        self.assertEqual(self.destination.read_bytes(), b'PREVIOUS_GOOD_FILE')

    def test_success_commits_new_file(self):
        with AtomicExport(self.destination) as export:
            export.path.write_bytes(b'NEW')
            export.commit()
        self.assertEqual(self.destination.read_bytes(), b'NEW')
        self.assertEqual(list(self.root.glob('.pg-export-*')), [])

    def test_source_cannot_be_overwritten(self):
        with self.assertRaises(ExportValidationError):
            with AtomicExport(self.destination, self.destination):
                self.fail('Source accepted as target')

    def test_concurrent_change_is_not_overwritten(self):
        with AtomicExport(self.destination) as export:
            export.path.write_bytes(b'new')
            self.destination.write_bytes(b'CHANGED_BY_ANOTHER_APP')
            with self.assertRaises(ExportValidationError):
                export.commit()
        self.assertEqual(self.destination.read_bytes(), b'CHANGED_BY_ANOTHER_APP')

    def test_new_destination_created_by_another_app_is_preserved(self):
        self.destination.unlink()
        with AtomicExport(self.destination) as export:
            export.path.write_bytes(b'new')
            self.destination.write_bytes(b'CONCURRENT')
            with self.assertRaises(ExportValidationError):
                export.commit()
        self.assertEqual(self.destination.read_bytes(), b'CONCURRENT')

    def test_hardlink_to_source_is_rejected(self):
        alias = self.root / 'alias.pdf'
        os.link(self.destination, alias)
        with self.assertRaises(ExportValidationError):
            with AtomicExport(alias, self.destination):
                self.fail('Hardlink accepted')

    def test_source_revision_rejects_replacement_and_deletion(self):
        source = self.root / "reviewed.docx"
        replacement = self.root / "replacement.docx"
        source.write_bytes(b"first")
        revision = SourceRevision.capture(source)
        revision.verify()
        replacement.write_bytes(b"later")
        os.replace(replacement, source)
        with self.assertRaisesRegex(ExportValidationError, "原件在打开后已更新"):
            revision.verify()
        current = SourceRevision.capture(source)
        source.unlink()
        with self.assertRaisesRegex(ExportValidationError, "原件在打开后已更新"):
            current.verify()

    def test_word_export_refuses_changed_original_and_keeps_existing_output(self):
        from docx import Document

        source = self.root / "reviewed.docx"
        target = self.root / "existing.docx"
        reviewed = Document()
        reviewed.add_paragraph("REVIEWED")
        reviewed.save(source)
        target.write_bytes(b"existing result")
        revision = SourceRevision.capture(source)
        reviewed.add_paragraph("SOURCE CHANGED")
        reviewed.save(source)
        with self.assertRaisesRegex(ExportValidationError, "原件在打开后已更新"):
            save_verified_docx(reviewed, target, source, source_revision=revision)
        self.assertEqual(target.read_bytes(), b"existing result")
        self.assertEqual(list(self.root.glob(".pg-export-*")), [])


class TestPDFExportValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'output.pdf'
        self.doc = fitz.open()
        self.addCleanup(self.doc.close)
        self.doc.new_page(width=300, height=200).insert_text((30, 60), 'SECRET PUBLIC')
        self.doc.set_toc([[1, 'PUBLIC BOOKMARK', 1]])
        rect = self.doc[0].search_for('SECRET')[0]
        self.area = rect
        self.data = {0: {'ocr': [{'rect': QRectF(rect.x0,rect.y0,rect.width,rect.height),
                                'replace_text': ''}], 'manual': []}}

    def test_black_rectangle_without_removal_is_rejected(self):
        self.doc[0].draw_rect(self.area, fill=(0,0,0), overlay=True)
        self.doc.save(self.path)
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path, self.doc, self.data, {})

    def test_anagram_of_requested_replacement_cannot_hide_residual(self):
        self.data[0]['ocr'][0]['replace_text']='TERCES'
        self.doc[0].draw_rect(self.area,fill=(0,0,0),overlay=True)
        self.doc.save(self.path)
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,self.data,{})

    def test_real_redaction_passes_and_preserves_other_text(self):
        self.doc[0].add_redact_annot(self.area)
        self.doc[0].apply_redactions()
        self.assertEqual(save_verified_pdf(self.doc,self.path,{'garbage':2},self.data),1)
        with fitz.open(self.path) as saved:
            self.assertNotIn('SECRET',saved[0].get_text())
            self.assertIn('PUBLIC',saved[0].get_text())

    def test_validation_failure_does_not_replace_good_target(self):
        self.path.write_bytes(b'PREVIOUS_GOOD')
        with self.assertRaises(ExportValidationError):
            save_verified_pdf(self.doc,self.path,{},self.data)
        self.assertEqual(self.path.read_bytes(),b'PREVIOUS_GOOD')

    def test_warned_export_can_be_saved_by_explicit_confirmation(self):
        seen = []

        def confirm(pages):
            seen.append(pages)
            return True

        self.assertEqual(save_verified_pdf(self.doc, self.path, {}, self.data,
                                          confirm_text_warnings=confirm), 1)
        self.assertEqual(seen, [(1,)])
        with fitz.open(self.path) as saved:
            self.assertIn("SECRET", saved[0].get_text())

    def test_returning_to_review_leaves_previous_result_unchanged(self):
        self.path.write_bytes(b"PREVIOUS_GOOD")
        self.assertIsNone(save_verified_pdf(self.doc, self.path, {}, self.data,
                                           confirm_text_warnings=lambda _pages: False))
        self.assertEqual(self.path.read_bytes(), b"PREVIOUS_GOOD")
        self.assertEqual(list(self.path.parent.glob(".pg-export-*")), [])

    def test_structure_errors_are_not_offered_the_text_override(self):
        called = []
        bad_masks = {6: self.data[0]}
        with self.assertRaisesRegex(ExportValidationError, "遮罩页码"):
            save_verified_pdf(self.doc, self.path, {}, bad_masks, confirm_text_warnings=called.append)
        self.assertEqual(called, [])
        self.assertFalse(self.path.exists())

    def test_changed_bookmark_is_rejected(self):
        with fitz.open(stream=self.doc.tobytes(),filetype='pdf') as other:
            other.set_toc([])
            other.save(self.path)
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{}, {})

    def test_changed_page_count_is_rejected(self):
        with fitz.open() as other:
            other.new_page()
            other.new_page()
            other.save(self.path)
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{}, {})

    def test_corrupted_output_is_rejected(self):
        self.path.write_bytes(b'not a PDF')
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{}, {})

    def test_mask_for_missing_page_is_not_silently_ignored(self):
        self.doc.save(self.path)
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{5:self.data[0]}, {})

    def test_wrong_open_password_is_rejected(self):
        kwargs={'encryption':fitz.PDF_ENCRYPT_AES_256,'owner_pw':'owner','user_pw':'open'}
        self.doc.save(self.path,**kwargs)
        kwargs['user_pw']='wrong'
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{},kwargs)

    def test_unexpected_permission_change_is_rejected(self):
        kwargs={'encryption':fitz.PDF_ENCRYPT_AES_256,'owner_pw':'owner','user_pw':'',
                'permissions':fitz.PDF_PERM_PRINT}
        self.doc.save(self.path,**kwargs)
        kwargs['permissions'] |= fitz.PDF_PERM_COPY
        with self.assertRaises(ExportValidationError):
            verify_pdf_export(self.path,self.doc,{},kwargs)

    def test_open_password_encryption_roundtrips(self):
        kwargs={'encryption':fitz.PDF_ENCRYPT_AES_256,'owner_pw':'owner','user_pw':'open'}
        save_verified_pdf(self.doc,self.path,kwargs,{})
        with fitz.open(self.path) as saved:
            self.assertTrue(saved.needs_pass)
            self.assertGreater(saved.authenticate('open'),0)

    def test_open_password_without_edit_password_roundtrips(self):
        from privacyguard.utils.helpers_pdf import build_encrypt_save_kwargs

        options = build_encrypt_save_kwargs("public-test-pass", "")
        save_verified_pdf(self.doc, self.path, options, {})
        with fitz.open(self.path) as saved:
            self.assertTrue(saved.needs_pass)
            self.assertGreater(saved.authenticate("public-test-pass"), 0)
            permissions = int(saved.xref_get_key(-1, "Encrypt/P")[1])
            self.assertTrue(permissions & fitz.PDF_PERM_FORM)
            self.assertTrue(permissions & fitz.PDF_PERM_ASSEMBLE)
            self.assertTrue(permissions & fitz.PDF_PERM_PRINT_HQ)

    def test_same_passwords_cannot_pass_restricted_edit_verification(self):
        from privacyguard.utils.helpers_pdf import build_encrypt_save_kwargs

        options = build_encrypt_save_kwargs("same-test-pass", "same-test-pass")
        with self.assertRaisesRegex(ExportValidationError, "编辑权限验证未通过"):
            save_verified_pdf(self.doc, self.path, options, {})

    def test_owner_only_encryption_roundtrips(self):
        kwargs={'encryption':fitz.PDF_ENCRYPT_AES_256,'owner_pw':'owner','user_pw':'',
                'permissions':fitz.PDF_PERM_PRINT}
        save_verified_pdf(self.doc,self.path,kwargs,{})

    def test_replacement_text_is_allowed(self):
        self.doc[0].add_redact_annot(self.area)
        self.doc[0].apply_redactions()
        self.doc[0].insert_text((self.area.x0,60),'MASK',fontsize=8)
        self.data[0]['ocr'][0]['replace_text']='MASK'
        save_verified_pdf(self.doc,self.path,{},self.data)

    def test_rotated_page_uses_display_masks(self):
        self.doc[0].set_rotation(90)
        rect=self.area*self.doc[0].rotation_matrix
        self.data[0]['ocr'][0]['rect']=QRectF(rect.x0,rect.y0,rect.width,rect.height)
        self.doc[0].add_redact_annot(self.area)
        self.doc[0].apply_redactions()
        save_verified_pdf(self.doc,self.path,{},self.data)

    def test_overlapping_masks_with_replacement_still_export(self):
        area2=self.area+(-2,-2,2,2)
        self.data[0]['manual']=[{'rect':QRectF(area2.x0,area2.y0,area2.width,area2.height),
                                'replace_text':'X'}]
        self.data[0]['ocr'][0]['replace_text']='MASK'
        for area in (self.area,area2):
            self.doc[0].add_redact_annot(area)
        self.doc[0].apply_redactions()
        self.doc[0].insert_text((self.area.x0,60),'MASK',fontsize=8)
        self.doc[0].insert_text((area2.x0,60),'X',fontsize=8)
        save_verified_pdf(self.doc,self.path,{},self.data)

    def test_same_sensitive_word_outside_mask_does_not_block_export(self):
        self.doc[0].insert_text((30,150),'SECRET ALLOWED OUTSIDE')
        self.doc[0].add_redact_annot(self.area)
        self.doc[0].apply_redactions()
        save_verified_pdf(self.doc,self.path,{},self.data)
        with fitz.open(self.path) as saved:
            self.assertIn('SECRET ALLOWED OUTSIDE',saved[0].get_text())

    def test_invalid_mask_rejected_without_leaking_contents(self):
        self.doc.save(self.path)
        self.data[0]['ocr'][0]['rect']=QRectF(1,1,float('nan'),20)
        with self.assertRaises(ExportValidationError) as caught:
            verify_pdf_export(self.path,self.doc,self.data,{})
        self.assertNotIn('SECRET',str(caught.exception))


class TestWordExportValidation(unittest.TestCase):
    def test_roundtrip_keeps_format_images_and_nested_text_parts(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as tmp:
            doc = Document()
            doc.add_paragraph('PUBLIC').runs[0].bold = True
            doc.add_table(rows=1,cols=1).cell(0,0).text='REDACTED'
            doc.sections[0].header.paragraphs[0].text='HEADER'
            path=Path(tmp)/'out.docx'
            self.assertGreater(save_verified_docx(doc,path),3)
            saved=Document(path)
            self.assertTrue(saved.paragraphs[0].runs[0].bold)
            self.assertEqual(saved.tables[0].cell(0,0).text,'REDACTED')
            self.assertEqual(saved.sections[0].header.paragraphs[0].text,'HEADER')

    def test_changed_word_content_is_rejected(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as tmp:
            original=Document()
            original.add_paragraph('REDACTED')
            other=Document()
            other.add_paragraph('SECRET')
            path=Path(tmp)/'out.docx'
            other.save(path)
            with self.assertRaises(ExportValidationError):
                verify_docx_export(path,original)

    def test_word_validator_failure_preserves_existing_target(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'out.docx'
            path.write_bytes(b'GOOD_PREVIOUS_FILE')
            with patch('privacyguard.utils.export_validation.verify_docx_export', side_effect=ExportValidationError('synthetic')):
                with self.assertRaises(ExportValidationError):
                    save_verified_docx(Document(),path)
            self.assertEqual(path.read_bytes(),b'GOOD_PREVIOUS_FILE')


if __name__ == '__main__':
    unittest.main()
