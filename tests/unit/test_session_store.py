# -*- coding: utf-8 -*-
"""cp88 回归测试：会话草稿存储（privacyguard/session_store.py）。

存储目录用 tmp 注入（SessionStore(base_dir=...)），不触碰真实应用数据目录。
"""
import json
import os
import shutil
import tempfile
import time
import unittest

from privacyguard.session_store import SessionStore, build_fingerprint


class SessionStoreTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pg_sess_test_")
        self.store = SessionStore(base_dir=os.path.join(self.tmp, "sessions"))
        # 伪 PDF 文件（指纹只看 stat，不校验内容格式）
        self.pdf = os.path.join(self.tmp, "案卷.pdf")
        with open(self.pdf, "wb") as f:
            f.write(b"%PDF-fake-content")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _sample_snapshot(self):
        return {
            0: {"ocr": [(1.0, 2.0, 3.0, 4.0, "X")], "manual": []},
            2: {"ocr": [], "manual": [(5.0, 6.0, 7.0, 8.0, "")]},
        }


class TestSaveLoadRoundtrip(SessionStoreTestBase):
    def test_roundtrip_exact_match(self):
        path = self.store.save_draft(self.pdf, self._sample_snapshot(),
                                     current_page=2, mask_color=(255, 0, 0))
        self.assertIsNotNone(path)
        draft, match = self.store.load_draft(self.pdf)
        self.assertEqual(match, "exact")
        self.assertEqual(draft["current_page"], 2)
        self.assertEqual(draft["mask_color"], [255, 0, 0])
        # 页码回 int、条目回 tuple
        self.assertEqual(draft["page_data"][0]["ocr"], [(1.0, 2.0, 3.0, 4.0, "X")])
        self.assertEqual(draft["page_data"][2]["manual"], [(5.0, 6.0, 7.0, 8.0, "")])

    def test_path_only_match_when_file_changed(self):
        self.store.save_draft(self.pdf, self._sample_snapshot())
        time.sleep(1.1)  # mtime 秒级精度
        with open(self.pdf, "ab") as f:
            f.write(b"changed")
        draft, match = self.store.load_draft(self.pdf)
        self.assertIsNotNone(draft)
        self.assertEqual(match, "path_only")

    def test_no_draft_returns_none(self):
        draft, match = self.store.load_draft(self.pdf)
        self.assertIsNone(draft)
        self.assertIsNone(match)

    def test_corrupted_json_returns_none(self):
        path = self.store.save_draft(self.pdf, self._sample_snapshot())
        with open(path, "w", encoding="utf-8") as f:
            f.write("{broken json")
        draft, match = self.store.load_draft(self.pdf)
        self.assertIsNone(draft)

    def test_missing_source_file_returns_none_fingerprint(self):
        self.assertIsNone(build_fingerprint(os.path.join(self.tmp, "不存在.pdf")))


class TestPdfSnap(SessionStoreTestBase):
    def test_snap_write_and_read(self):
        data = b"%PDF-snapshot-bytes"
        self.store.save_draft(self.pdf, self._sample_snapshot(),
                              pdf_modified=True, pdf_bytes=data)
        draft, _ = self.store.load_draft(self.pdf)
        self.assertIsNotNone(draft["pdf_snap"])
        self.assertEqual(self.store.load_pdf_snap(self.pdf), data)

    def test_light_save_keeps_existing_snap(self):
        # 先带字节流保存，再纯遮罩轻量保存（pdf_modified 仍 True）→ 旁文件保留
        self.store.save_draft(self.pdf, self._sample_snapshot(),
                              pdf_modified=True, pdf_bytes=b"AA")
        self.store.save_draft(self.pdf, self._sample_snapshot(),
                              pdf_modified=True, pdf_bytes=None)
        draft, _ = self.store.load_draft(self.pdf)
        self.assertIsNotNone(draft["pdf_snap"])
        self.assertEqual(self.store.load_pdf_snap(self.pdf), b"AA")

    def test_no_snap_returns_none(self):
        self.store.save_draft(self.pdf, self._sample_snapshot())
        self.assertIsNone(self.store.load_pdf_snap(self.pdf))


class TestManagement(SessionStoreTestBase):
    def _make_pdf(self, name):
        p = os.path.join(self.tmp, name)
        with open(p, "wb") as f:
            f.write(b"%PDF" + name.encode("utf-8"))
        return p

    def test_delete_draft(self):
        self.store.save_draft(self.pdf, self._sample_snapshot(),
                              pdf_modified=True, pdf_bytes=b"S")
        self.store.delete_draft(self.pdf)
        draft, _ = self.store.load_draft(self.pdf)
        self.assertIsNone(draft)
        self.assertIsNone(self.store.load_pdf_snap(self.pdf))

    def test_prune_keeps_recent(self):
        paths = [self._make_pdf(f"f{i}.pdf") for i in range(5)]
        for i, p in enumerate(paths):
            self.store.save_draft(p, self._sample_snapshot())
            # 用 saved_at 排序：手动改草稿时间以保证次序确定
            draft_file = self.store._draft_path(p)
            with open(draft_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            d["saved_at"] = 1000 + i
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(d, f)
        self.store.prune_drafts(keep=2)
        remaining = self.store.list_drafts()
        self.assertEqual(len(remaining), 2)
        # 留下的是 saved_at 最大的两份
        self.assertEqual([s for _, s in remaining], [1004, 1003])

    def test_clear_all(self):
        for name in ("a.pdf", "b.pdf"):
            self.store.save_draft(self._make_pdf(name), self._sample_snapshot())
        self.assertEqual(self.store.clear_all(), 2)
        self.assertEqual(self.store.list_drafts(), [])


if __name__ == "__main__":
    unittest.main()
