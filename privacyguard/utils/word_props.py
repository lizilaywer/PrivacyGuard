"""Word 文档元数据清除 (Phase 3 G2 Gap 4 / SAFE-03 Word 子项)。

与 Phase 2 PDF metadata clearing 同策略: 清空 5 个标准 core_properties
(Title / Author / Subject / Comments / Keywords), 设置为空字符串而非占位符
(D-15: 占位符字符串仍可能在 audit 报告 / forensic 工具中被发现, 空字符串才是
"完全清除" 语义)。调用方持有 python-docx Document 句柄传入 (与 word_adapter
三函数同形态: 不在 helper 内 import python-docx, 仅 type hint forward ref)。

公开 API:
- clear_word_core_properties(doc, keys=None): 清空 Document.core_properties
  指定字段。keys=None 时清空 5 个标准字段 (D-15 默认集)。
- DEFAULT_KEYS: 5 个标准字段名 tuple, 供外部扩展时复用。
"""
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # 仅类型检查期; runtime 不 import python-docx
    from docx import Document  # noqa: F401


DEFAULT_KEYS = ("title", "author", "subject", "comments", "keywords")


def clear_word_core_properties(
    doc: "Document",
    keys: Optional[Iterable[str]] = None,
) -> int:
    """清空 doc.core_properties 指定字段; 返回清空字段数。

    Args:
        doc: python-docx Document (调用方持有句柄, 不在 helper 内 import docx)
        keys: 要清空的字段名 iterable; None 时使用 DEFAULT_KEYS
              (title / author / subject / comments / keywords)

    Returns:
        int: 实际写入清空字符串的字段数 (Phase 3 G2 反向提取验证用)
    """
    target_keys = tuple(keys) if keys is not None else DEFAULT_KEYS
    cp = doc.core_properties
    cleared = 0
    for key in target_keys:
        try:
            current = getattr(cp, key, None)
        except Exception:
            continue
        if current is None:
            continue
        setattr(cp, key, "")
        cleared += 1
    return cleared