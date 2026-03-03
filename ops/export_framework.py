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

def add_tree(z: zipfile.ZipFile, folder: Path, arc_prefix: str) -> None:
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            rel = p.relative_to(folder).as_posix()
            arc = f"{arc_prefix}/{rel}" if rel else arc_prefix
            zip_write_bytes(z, arc, p.read_bytes())

def main() -> None:
    # Framework-only export (no canon/, no overlays/)
    out_dir = ROOT / "packs" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"framework_export_{utc_stamp()}.zip"

    with zipfile.ZipFile(out, "w") as z:
        add_tree(z, ROOT / "core", "core")
        add_tree(z, ROOT / "ops", "ops")
        add_tree(z, ROOT / "docs", "docs")
        add_tree(z, ROOT / "canon_template", "canon_template")
        if (ROOT / ".github").exists():
            add_tree(z, ROOT / ".github", ".github")

        # Root files (if present)
        for fn in [".gitattributes", ".gitignore", "README.md"]:
            p = ROOT / fn
            if p.exists() and p.is_file():
                zip_write_bytes(z, fn, p.read_bytes())

        # Newbie one-click launchers (if present)
        for fn in ["RUN_DOCTOR.bat", "MAKE_PACK.bat", "APPLY_LATEST.bat", "EXPORT_FRAMEWORK.bat", "EXPORT_NEWBIE_PACK.bat"]:
            p = ROOT / fn
            if p.exists() and p.is_file():
                zip_write_bytes(z, fn, p.read_bytes())

    print(str(out))

if __name__ == "__main__":
    main()
