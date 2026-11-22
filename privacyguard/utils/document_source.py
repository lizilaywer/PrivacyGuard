"""Track the on-disk revision associated with a document preview."""

import os
from dataclasses import dataclass

from .export_transaction import ExportValidationError


@dataclass(frozen=True)
class SourceRevision:
    path: str
    identity: tuple[int, int, int, int, int]

    @classmethod
    def capture(cls, path):
        path = os.path.abspath(path)
        info = os.stat(path)
        return cls(path, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))

    def verify(self):
        try:
            if self.capture(self.path) == self:
                return
        except OSError:
            pass
        raise ExportValidationError("原件在打开后已更新或无法访问。请重新打开文件并检查遮罩。")
