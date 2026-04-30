from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VERSION_FILE = PROJECT_ROOT / "version.txt"
OUTPUT_FILE = PROJECT_ROOT / "packaging" / "windows" / "config" / "version_info.txt"


def load_version():
    version_text = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version_text:
        raise ValueError("version.txt is empty")

    parts = [int(part) for part in version_text.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return version_text, tuple(parts[:4])


def build_version_info(version_text, version_tuple):
    version_string = ".".join(str(part) for part in version_tuple)
    version_tuple_text = ", ".join(str(part) for part in version_tuple)
    return f"""# UTF-8
# Generated from version.txt by packaging/windows/scripts/generate_version_info.py

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple_text}),
    prodvers=({version_tuple_text}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'080404B0',
        [
          StringStruct(u'CompanyName', u'PrivacyGuard Team'),
          StringStruct(u'FileDescription', u'PrivacyGuard 脱敏卫士'),
          StringStruct(u'FileVersion', u'{version_string}'),
          StringStruct(u'InternalName', u'PrivacyGuard'),
          StringStruct(u'LegalCopyright', u'Copyright (C) 2026 PrivacyGuard Team'),
          StringStruct(u'OriginalFilename', u'PrivacyGuard.exe'),
          StringStruct(u'ProductName', u'PrivacyGuard 脱敏卫士'),
          StringStruct(u'ProductVersion', u'{version_string}')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
"""


def main():
    version_text, version_tuple = load_version()
    OUTPUT_FILE.write_text(build_version_info(version_text, version_tuple), encoding="utf-8")
    print(f"[OK] Generated {OUTPUT_FILE} from version {version_text}")


if __name__ == "__main__":
    main()
