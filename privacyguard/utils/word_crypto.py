# -*- coding: utf-8 -*-
"""PrivacyGuard Word 文档加密检测与解密工具。

cp113: 支持打开受密码保护的 .docx 文档。

技术约束：
- python-docx 不能直接读取加密 docx（OLE2 容器，非 ZIP），需先用 msoffcrypto 解密。
- python-docx 不支持加密保存，故 Word 仅"打开 + 解除密码"，不支持"修改密码后重新加密"。

提供:
- is_encrypted_docx(path): 检测 docx 是否加密（OLE2 魔数 D0 CF 11 E0）
- decrypt_docx_to_temp(path, password, output_path): msoffcrypto 解密到指定输出路径
"""

import os

__all__ = [
    "is_encrypted_docx",
    "decrypt_docx_to_temp",
]


# OLE2 复合文档魔数（加密 Office 文档容器头）
# 普通 docx 是 ZIP 容器，头为 50 4B 03 04（PK..）
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0"
_ZIP_MAGIC = b"PK\x03\x04"


def is_encrypted_docx(path):
    """检测 docx 文件是否为加密的 OLE2 容器。

    判据：文件头前 4 字节为 OLE2 魔数 D0 CF 11 E0 → 加密；
          为 ZIP 魔数 PK\\x03\\x04 → 普通 docx。
          其他或读取失败 → False（交由上层错误处理）。

    Args:
        path: docx 文件路径

    Returns:
        bool: True 表示加密（需密码解密），False 表示普通 docx 或无法判定
    """
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(4)
    except OSError:
        return False
    return head == _OLE2_MAGIC


def decrypt_docx_to_temp(path, password, output_path):
    """用 msoffcrypto 解密加密 docx 到指定输出路径。

    懒导入 msoffcrypto（与 OCR 懒加载原则一致，避免顶部硬依赖）。
    调用方负责 output_path 所在目录的创建与生命周期管理（通常用 TempFileManager 追踪）。

    Args:
        path: 加密 docx 文件路径
        password: 打开密码
        output_path: 解密后 docx 写入的完整路径（调用方控制命名，便于保留原 basename）

    Returns:
        str: 解密后的 docx 文件路径（即 output_path）

    Raises:
        TypeError: 文件不是加密 docx（非 OLE2 容器）
        ValueError: 密码错误或解密失败
        OSError: 临时文件写入失败
    """
    if not is_encrypted_docx(path):
        raise TypeError(f"不是加密 docx：{path}")

    try:
        import msoffcrypto  # type: ignore[import-not-found]
    except ImportError as e:
        raise OSError(
            "未安装 msoffcrypto-tool，无法解密 Word 文档。"
            "请运行：pip install msoffcrypto-tool"
        ) from e

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        with open(path, "rb") as in_fp:
            office_file = msoffcrypto.OfficeFile(in_fp)
            try:
                office_file.load_key(password=password)
            except Exception as e:
                raise ValueError(f"密码不正确或解密失败：{e}") from e
            try:
                with open(output_path, "wb") as out:
                    office_file.decrypt(out)
            except Exception as e:
                raise ValueError(f"解密失败：{e}") from e
    except ValueError:
        # 密码错误：清理半成品文件后向上抛
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass
        raise
    except Exception:
        # 其他异常也清理半成品文件
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass
        raise

    return output_path
