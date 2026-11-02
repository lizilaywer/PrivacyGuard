# -*- coding: utf-8 -*-
"""cp88: 脱敏会话草稿存储（会话恢复 A1）。

设计（D1 铁律：纯逻辑不依赖 GUI/Qt）：
- 草稿集中存放于应用数据目录 sessions/ 下，不在用户 PDF 旁生成 sidecar
- 指纹 = 路径 + 文件大小 + mtime；草稿文件名 = sha1(路径)[:16] + .pgdraft.json
- 轻重分离：遮罩数据（元组结构，来自 snapshot_page_data）只写轻量 JSON；
  页面结构被修改过（旋转/插入/删除）时 doc 字节流写同名 .pdfsnap 旁文件
- 损坏 JSON 容错返回 None，不抛异常
"""
import hashlib
import json
import logging
import os
import time

logger = logging.getLogger(__name__)


DRAFT_VERSION = 1


def _default_base_dir():
    """应用数据目录（延迟计算，测试可注入 base_dir 覆盖）。"""
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        root = os.path.expanduser("~/Library/Application Support") \
            if os.uname().sysname == "Darwin" else os.path.expanduser("~/.local/share")
    return os.path.join(root, "PrivacyGuard", "sessions")


def build_fingerprint(pdf_path):
    """构造文件指纹 dict；文件不存在返回 None。"""
    try:
        st = os.stat(pdf_path)
    except OSError:
        return None
    return {
        # 安全审计 v40.1: 不存绝对路径（含用户名），只用 size+mtime 做指纹比对
        "size": st.st_size,
        "mtime": int(st.st_mtime),
    }


def _draft_key(pdf_path):
    normalized = os.path.abspath(pdf_path or "").lower()
    return hashlib.sha1(normalized.encode("utf-8", "replace")).hexdigest()[:16]


class SessionStore:
    """草稿读写（每个 PDF 路径一份草稿，新的覆盖旧的）。"""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or _default_base_dir()

    # --- 路径 ---

    def _draft_path(self, pdf_path):
        return os.path.join(self.base_dir, _draft_key(pdf_path) + ".pgdraft.json")

    def _snap_path(self, pdf_path):
        return os.path.join(self.base_dir, _draft_key(pdf_path) + ".pdfsnap")

    # --- 写 ---

    def save_draft(self, pdf_path, page_data_snapshot, current_page=0,
                   mask_color=(0, 0, 0), pdf_modified=False, pdf_bytes=None):
        """保存草稿。pdf_bytes 仅结构修改时传入（写旁文件）；None 保留已有旁文件。

        Returns: 草稿路径；失败返回 None（不抛）。
        """
        fp = build_fingerprint(pdf_path)
        if fp is None:
            return None
        try:
            # 安全审计 v40.1.4：sessions 目录收紧为 0700（pdfsnap 是未脱敏原文完整副本）
            os.makedirs(self.base_dir, mode=0o700, exist_ok=True)
            try:
                os.chmod(self.base_dir, 0o700)
            except OSError:
                pass
            snap_file = None
            if pdf_bytes:
                snap_file = self._snap_path(pdf_path)
                # 0600：未脱敏原文快照，防多用户主机同机账户可读
                _fd = os.open(snap_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(_fd, "wb") as f:
                    f.write(pdf_bytes)
            elif pdf_modified and os.path.exists(self._snap_path(pdf_path)):
                snap_file = self._snap_path(pdf_path)  # 沿用已有结构快照

            draft = {
                "version": DRAFT_VERSION,
                "fingerprint": fp,
                "saved_at": time.time(),
                "current_page": int(current_page),
                "mask_color": list(mask_color),
                "pdf_modified": bool(pdf_modified),
                "pdf_snap": os.path.basename(snap_file) if snap_file else None,
                # page_data 快照：{页码(str): {"ocr": [[x,y,w,h,replace]...], ...}}
                "page_data": {
                    str(pn): {k: [list(t) for t in items]
                              for k, items in entry.items()}
                    for pn, entry in (page_data_snapshot or {}).items()
                },
            }
            path = self._draft_path(pdf_path)
            tmp = path + ".tmp"
            # 0600：草稿含遮罩元数据（0600 与 pdfsnap 一致的敏感等级）
            _fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(_fd, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False)
            os.replace(tmp, path)  # 原子替换，避免半截文件
            return path
        except OSError as e:
            # 安全审计 v40.1: 不打印异常 message（可能含路径），只记类型
            logger.warning("[cp88] 草稿保存失败: %s", type(e).__name__)
            return None

    # --- 读 ---

    def load_draft(self, pdf_path):
        """加载草稿并核对指纹。

        Returns:
            (draft_dict, match) — match 为 "exact"（指纹全匹配）或
            "path_only"（路径匹配但 size/mtime 变化）；无草稿/损坏返回 (None, None)。
            draft_dict["page_data"] 已还原为 {int页码: {"ocr": [(x,y,w,h,replace)...]}}。
        """
        path = self._draft_path(pdf_path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                draft = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None, None
        if not isinstance(draft, dict) or draft.get("version") != DRAFT_VERSION:
            return None, None

        current_fp = build_fingerprint(pdf_path)
        saved_fp = draft.get("fingerprint") or {}
        if not isinstance(saved_fp, dict):
            return None, None
        if current_fp is None:
            return None, None
        match = "exact" if (saved_fp.get("size") == current_fp["size"]
                            and saved_fp.get("mtime") == current_fp["mtime"]) else "path_only"

        try:
            restored = {}
            for pn_str, entry in (draft.get("page_data") or {}).items():
                restored[int(pn_str)] = {
                    k: [tuple(t) for t in items] for k, items in entry.items()
                }
            draft["page_data"] = restored
        except (ValueError, TypeError, AttributeError):
            return None, None
        return draft, match

    def load_pdf_snap(self, pdf_path):
        """读取结构快照字节流；无/失败返回 None。"""
        try:
            with open(self._snap_path(pdf_path), "rb") as f:
                return f.read()
        except OSError:
            return None

    # --- 管理 ---

    def delete_draft(self, pdf_path):
        for p in (self._draft_path(pdf_path), self._snap_path(pdf_path)):
            try:
                os.remove(p)
            except OSError:
                pass

    def list_drafts(self):
        """返回 [(草稿路径, saved_at)]，按时间降序；目录不存在返回空。"""
        try:
            names = os.listdir(self.base_dir)
        except OSError:
            return []
        out = []
        for name in names:
            if not name.endswith(".pgdraft.json"):
                continue
            full = os.path.join(self.base_dir, name)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    record = json.load(f)
                    saved_at = float(record.get("saved_at", 0)) if isinstance(record, dict) else 0
            except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
                saved_at = 0
            out.append((full, saved_at))
        out.sort(key=lambda t: t[1], reverse=True)
        return out

    def prune_drafts(self, keep=20):
        """LRU 淘汰：保留最近 keep 份，删除更旧的（含其 pdfsnap 旁文件）。"""
        removed = 0
        for full, _saved in self.list_drafts()[keep:]:
            snap = full.replace(".pgdraft.json", ".pdfsnap")
            for p in (full, snap):
                try:
                    os.remove(p)
                    removed += 1
                except OSError:
                    pass
        return removed

    def clear_all(self):
        """清空全部草稿，返回删除的草稿份数。"""
        count = 0
        for full, _saved in self.list_drafts():
            snap = full.replace(".pgdraft.json", ".pdfsnap")
            for p in (full, snap):
                try:
                    os.remove(p)
                except OSError:
                    pass
            count += 1
        return count
