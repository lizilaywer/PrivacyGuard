"""创建测试用 PII PDF —— 含文字层敏感信息（身份证 / 手机号）。

Phase 1 仅生成文字型测试 PDF；扫描型 / 跨行样本由 Plan 01-02 / 01-03 扩展。
Phase 1 不引入 reportlab 依赖，统一使用 PyMuPDF `fitz` `insert_text`。
"""
import fitz

from tests.fixtures.fake_pii import fake_id_card, fake_phone


def create_pii_test_pdf(output_path: str) -> str:
    """生成含一个 18 位身份证 + 一个 11 位手机号的文字层测试 PDF。

    返回 output_path；幂等（每次运行重新合成新随机号码）。
    """
    doc = fitz.open()
    page = doc.new_page()
    secret_id = fake_id_card()
    secret_phone = fake_phone()
    # 文字层一行（中文 + ID + 手机号）
    page.insert_text(
        (50, 100),
        f"测试样本 身份证 {secret_id} 手机 {secret_phone}",
        fontsize=14,
    )
    doc.save(output_path)
    doc.close()
    return output_path


def create_pii_id_only_pdf(output_path: str) -> str:
    """生成仅含 18 位身份证的文字层 PDF（用于隔离验证）。"""
    doc = fitz.open()
    page = doc.new_page()
    secret_id = fake_id_card()
    page.insert_text((50, 100), f"测试样本 身份证 {secret_id}", fontsize=14)
    doc.save(output_path)
    doc.close()
    return output_path


def create_pii_phone_only_pdf(output_path: str) -> str:
    """生成仅含 11 位手机号的文字层 PDF（用于隔离验证）。"""
    doc = fitz.open()
    page = doc.new_page()
    secret_phone = fake_phone()
    page.insert_text((50, 100), f"测试样本 手机 {secret_phone}", fontsize=14)
    doc.save(output_path)
    doc.close()
    return output_path


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pii_test.pdf"
    print(f"生成 PII 测试 PDF -> {create_pii_test_pdf(target)}")