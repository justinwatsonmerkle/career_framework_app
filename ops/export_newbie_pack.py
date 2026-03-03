#!/usr/bin/env python3
import datetime
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_FIXED_TIME = (1980, 1, 1, 0, 0, 0)

def utc_stamp() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat().replace(":", "").replace("-", "") + "Z"

def zip_write_bytes(z: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname)
    info.date_time = ZIP_FIXED_TIME
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)

def main() -> None:
    out_dir = ROOT / "packs" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"newbie_pack_{utc_stamp()}.zip"

    include_files = [
        "RUN_DOCTOR.bat",
        "MAKE_PACK.bat",
        "APPLY_LATEST.bat",
        "EXPORT_FRAMEWORK.bat",
        "EXPORT_NEWBIE_PACK.bat",
        "docs/START_HERE.md",
        "docs/START_CHAT_ROUTER.txt",
        "docs/troubleshooting.md",
        "ops/doctor.py",
        "ops/fix_text_hygiene.py",
        "ops/apply_latest.py",
        "ops/requirements.txt",
    ]

    with zipfile.ZipFile(out, "w") as z:
        for rel in include_files:
            p = ROOT / rel
            if p.exists() and p.is_file():
                zip_write_bytes(z, rel, p.read_bytes())

    print(str(out))

if __name__ == "__main__":
    main()
