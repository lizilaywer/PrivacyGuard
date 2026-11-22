"""Write, reopen and verify exports before replacing a user's destination.

Temporary files stay in the destination directory (same filesystem, mode 0600).
There is deliberately no delete-first or non-atomic copy fallback.
"""

import os
import tempfile
from pathlib import Path


class ExportValidationError(RuntimeError):
    """A candidate output failed a specific check; it must not be published."""


def _file_identity(path):
    try:
        info = os.stat(path, follow_symlinks=False)
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
    except FileNotFoundError:
        return None


class AtomicExport:
    """An output transaction; commit is explicit and must follow validation."""

    def __init__(self, destination, source_path=None):
        self.destination = Path(os.path.abspath(os.fspath(destination)))
        self.source_path = source_path
        self.path = None
        self._original_identity = None
        self._parent_identity = None

    def _check_source(self):
        if not self.source_path:
            return
        target = os.path.realpath(self.destination)
        sources = self.source_path if isinstance(self.source_path, (list, tuple)) else [self.source_path]
        for candidate in sources:
            if not candidate:
                continue
            source = os.path.realpath(candidate)
            same = os.path.normcase(source) == os.path.normcase(target)
            if not same and os.path.exists(source) and self.destination.exists():
                same = os.path.samefile(source, self.destination)
            if same:
                raise ExportValidationError("请另存为新文件，保留原始文档。")

    def __enter__(self):
        self._check_source()
        if self.destination.is_symlink():
            raise ExportValidationError("导出目标是链接，请选择一个普通文件路径。")
        info = self.destination.parent.stat()
        self._parent_identity = info.st_dev, info.st_ino
        self._original_identity = _file_identity(self.destination)
        fd, name = tempfile.mkstemp(prefix=".pg-export-", suffix=self.destination.suffix,
                                    dir=self.destination.parent)
        os.close(fd)
        self.path = Path(name)
        return self

    def commit(self):
        self._check_source()
        info = self.destination.parent.stat()
        if (info.st_dev, info.st_ino) != self._parent_identity:
            raise ExportValidationError("导出文件夹已改变，请重新选择保存位置。")
        if _file_identity(self.destination) != self._original_identity:
            raise ExportValidationError("目标文件刚被其他程序修改，请重新保存。")
        with self.path.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(self.path, self.destination)
        self.path = None

    def __exit__(self, *_args):
        if self.path is not None:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass  # retain restrictive mode on an occupied temporary file


def save_verified_pdf(document, destination, save_kwargs, page_data, source_path=None, policy="preserve",
                      *, source_revision=None):
    """Atomic PDF save with closed-handle reopen verification; returns check count."""
    from .export_validation import verify_pdf_export

    with AtomicExport(destination, source_path) as output:
        document.save(str(output.path), **save_kwargs)
        checked = verify_pdf_export(output.path, document, page_data, save_kwargs)
        if policy != "preserve":
            import fitz
            from .pdf_sanitize import verify_pdf_policy
            with fitz.open(output.path) as saved:
                password = save_kwargs.get("owner_pw") or save_kwargs.get("user_pw")
                if password and saved.authenticate(password) <= 0:
                    raise ExportValidationError("无法认证并复查导出文件。")
                verify_pdf_policy(saved, policy)
        if source_revision is not None:
            source_revision.verify()
        output.commit()
        return checked


def save_verified_docx(document, destination, source_path=None, *, source_revision=None):
    """Reopen DOCX and compare every document part before atomic publication.

    This ensures the intended edited package was saved intact; it does not
    extend the set of Word parts supported by the redaction rules.
    """
    from .export_validation import verify_docx_export

    with AtomicExport(destination, source_path) as output:
        document.save(str(output.path))
        checked = verify_docx_export(output.path, document)
        if source_revision is not None:
            source_revision.verify()
        output.commit()
        return checked
