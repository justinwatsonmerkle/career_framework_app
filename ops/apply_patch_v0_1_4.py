#!/usr/bin/env python3
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ZIP_FIXED_TIME = (1980, 1, 1, 0, 0, 0)

def write_text(rel: str, content: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    p.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8", newline="\n")

def ensure_dir(rel: str) -> None:
    (ROOT / rel).mkdir(parents=True, exist_ok=True)

def ensure_keep(rel: str) -> None:
    ensure_dir(rel)
    (ROOT / rel / ".keep").write_text("", encoding="utf-8", newline="\n")

def patch_gitignore() -> None:
    p = ROOT / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    lines = [ln.rstrip("\n") for ln in existing.replace("\r\n", "\n").replace("\r", "\n").split("\n") if ln is not None]

    def has(pattern: str) -> bool:
        return any(ln.strip() == pattern for ln in lines)

    # Keep packs out of git, keep zip outputs out of git
    if not has("packs/"):
        lines.append("")
        lines.append("# Generated outputs")
        lines.append("packs/")
    if not any(ln.strip() == "*.zip" for ln in lines):
        lines.append("*.zip")

    p.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")

def stamp() -> str:
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

def patch_bundle_pack_to_outgoing() -> None:
    p = ROOT / "ops/bundle_pack.py"
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")

    # If already patched, leave it.
    if 'PACKS_DIR = ROOT / "packs" / "outgoing"' in txt:
        return

    # Replace the out_path assignment if it is the old root output.
    txt2 = re.sub(
        r"out_path\s*=\s*ROOT\s*/\s*pack_name",
        'PACKS_DIR = ROOT / "packs" / "outgoing"\n        PACKS_DIR.mkdir(parents=True, exist_ok=True)\n\n        out_path = PACKS_DIR / pack_name',
        txt,
        flags=re.M,
    )
    p.write_text(txt2, encoding="utf-8", newline="\n")

def write_export_framework_py() -> None:
    write_text("ops/export_framework.py", """\
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
""")

def write_export_newbie_pack_py() -> None:
    write_text("ops/export_newbie_pack.py", """\
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
""")

def write_apply_latest_py() -> None:
    write_text("ops/apply_latest.py", """\
#!/usr/bin/env python3
import sys
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent

def main() -> None:
    incoming = ROOT / "packs" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    zips = sorted(incoming.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        print("No incoming zip found in packs/incoming")
        sys.exit(1)

    pack = zips[0]
    print(f"Applying: {pack}")

    r = subprocess.run([sys.executable, str(ROOT / "ops/apply.py"), str(pack)], cwd=str(ROOT))
    sys.exit(r.returncode)

if __name__ == "__main__":
    main()
""")

def write_bat_launchers() -> None:
    # These are intentionally dumb and obvious.
    write_text("RUN_DOCTOR.bat", """\
@echo off
cd /d "%~dp0"
py -3 ops\\doctor.py --fix
pause
""")
    write_text("MAKE_PACK.bat", """\
@echo off
cd /d "%~dp0"
py -3 ops\\make_pack.py
pause
""")
    write_text("APPLY_LATEST.bat", """\
@echo off
cd /d "%~dp0"
py -3 ops\\apply_latest.py
pause
""")
    write_text("EXPORT_FRAMEWORK.bat", """\
@echo off
cd /d "%~dp0"
py -3 ops\\export_framework.py
pause
""")
    write_text("EXPORT_NEWBIE_PACK.bat", """\
@echo off
cd /d "%~dp0"
py -3 ops\\export_newbie_pack.py
pause
""")

def write_newbie_docs() -> None:
    write_text("docs/START_HERE.md", """\
# Start here (Windows)

1) Install deps (one time):
py -3 -m pip install --user -r ops\\requirements.txt

2) Preflight:
Double click RUN_DOCTOR.bat

3) Start a new chat:
Open docs/START_CHAT_ROUTER.txt and paste it into ChatGPT.

4) Save state for the next chat:
Double click MAKE_PACK.bat
Your pack will be in packs\\outgoing\\

5) Apply a pack you got from ChatGPT:
Put the zip into packs\\incoming\\ then double click APPLY_LATEST.bat
""")

    write_text("docs/START_CHAT_ROUTER.txt", """\
You are operating Career Framework.

Inputs:
- I may attach a framework export zip (core/ ops/ docs/ canon_template) if needed.
- I may attach my latest resume pack zip (canon-only) if I have one.

Rules:
- Use British English spelling.
- One mode per session.
- Do not output any updated canon files unless I explicitly say CHECKPOINT or WRAP_UP.
- Controlled publishing: on CHECKPOINT or WRAP_UP output a single zip containing only updated canon artefacts (full files, correct paths). Do not paste file contents in chat.
- Omission is not deletion.
- Side-question rule: answer briefly without switching modes, capture it into canon/backlog.md with TargetMode + Domain, then continue current mode.

Mode: ROUTER
Timebox: 30 minutes
Task: Recommend the best mode for this session. Output:
- Recommended mode
- One-sentence task statement
- Timebox (10/30/60; default 30 unless I state otherwise)
- Copy/paste start prompt for the chosen mode
Ask up to 5 questions first if needed.
""")

def patch_pack_maintenance_for_exports() -> None:
    p = ROOT / "ops/pack_maintenance.py"
    if not p.exists():
        return

    # Overwrite with a version that also archives exports.
    write_text("ops/pack_maintenance.py", """\
#!/usr/bin/env python3
import sys
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def _load_settings():
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ops.settings import load_settings
        return load_settings()
    except Exception:
        return {}

def _as_int(v, default):
    try:
        return int(v)
    except Exception:
        return default

def _move_old(files, keep_last, archive_dir):
    archive_dir.mkdir(parents=True, exist_ok=True)
    for p in files[keep_last:]:
        target = archive_dir / p.name
        if target.exists():
            target = archive_dir / f"{p.stem}_{int(time.time())}.zip"
        shutil.move(str(p), str(target))

def main():
    settings = _load_settings()
    packs_cfg = settings.get("packs", {}) if isinstance(settings.get("packs", {}), dict) else {}

    outgoing = ROOT / packs_cfg.get("outgoingDir", "packs/outgoing")
    archive = ROOT / packs_cfg.get("archiveDir", "packs/archive")
    exports = ROOT / packs_cfg.get("exportDir", "packs/exports")

    keep_last = _as_int(packs_cfg.get("keepLast", 20), 20)
    keep_exports = _as_int(packs_cfg.get("keepExports", 10), 10)

    outgoing.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    outgoing_packs = sorted(outgoing.glob("canon_pack_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    export_zips = sorted(exports.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    _move_old(outgoing_packs, keep_last, archive)
    _move_old(export_zips, keep_exports, archive / "exports")

    print("PACK_MAINTENANCE OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

def patch_doctor_to_autofix_hygiene() -> None:
    p = ROOT / "ops/doctor.py"
    if not p.exists():
        return

    # Overwrite doctor with a beginner-friendly version.
    write_text("ops/doctor.py", """\
#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
import subprocess
import datetime
import hashlib

ROOT = Path(__file__).resolve().parent.parent

def run(cmd):
    r = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout.strip()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def write_baseline_manifest():
    canon = ROOT / "canon"
    meta = canon / "meta.yml"
    manifest_path = canon / "pack_manifest.json"

    if not canon.exists():
        return

    meta_txt = meta.read_text(encoding="utf-8") if meta.exists() else ""
    def get_val(key):
        for ln in meta_txt.splitlines():
            if ln.startswith(key + ":"):
                parts = ln.split('"')
                if len(parts) >= 2:
                    return parts[1]
        return ""

    schema_version = get_val("schemaVersion") or "1"
    framework_version = get_val("frameworkVersion") or ""
    change_id = get_val("changeId") or "CHG-0000"

    created_at = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    files = []
    for p in sorted(canon.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel == "canon/pack_manifest.json":
            continue
        if rel.startswith("canon/logs/archive/"):
            continue
        data = p.read_bytes()
        files.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)})

    manifest = {
        "schemaVersion": schema_version,
        "frameworkVersion": framework_version,
        "baseChangeId": change_id,
        "publishedChangeId": change_id,
        "createdAt": created_at,
        "packFiles": [],
        "deleted": [],
        "files": files,
    }

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    manifest["manifestSha256"] = sha256_bytes(canonical)

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\\n", encoding="utf-8", newline="\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Apply safe fixes (bootstrap and hygiene)")
    ap.add_argument("--full", action="store_true", help="Also run ops/self_test.py")
    args = ap.parse_args()

    problems = []

    if sys.version_info < (3, 11):
        problems.append("Python is below 3.11. Use Python 3.11+.")

    try:
        import yaml  # noqa: F401
    except Exception:
        problems.append("Missing dependency: pyyaml. Install: py -3 -m pip install --user -r ops\\\\requirements.txt")

    # If this is a framework-only repo, we can still run lint. If this is an instance repo, canon will exist.
    canon = ROOT / "canon"
    canon_template = ROOT / "canon_template"

    # Bootstrap canon from canon_template if missing (for framework repo checks)
    if not canon.exists() and canon_template.exists() and args.fix:
        shutil_copy = True
        try:
            import shutil
            shutil.copytree(canon_template, canon, dirs_exist_ok=True)
        except Exception as e:
            problems.append(f"Failed to bootstrap canon from canon_template: {e}")

    # Settings bootstrap
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ops.settings import bootstrap_settings_if_missing
        if args.fix:
            bootstrap_settings_if_missing()
    except Exception as e:
        problems.append(f"Settings bootstrap failed: {e}")

    # Baseline manifest
    manifest = canon / "pack_manifest.json"
    if canon.exists():
        if not manifest.exists() and args.fix:
            try:
                write_baseline_manifest()
            except Exception as e:
                problems.append(f"Failed to create baseline manifest: {e}")

    # Auto-fix smart punctuation when requested
    if canon.exists() and args.fix:
        run([sys.executable, "ops/fix_text_hygiene.py", "canon", "--apply"])

    # Lint
    code, out = run([sys.executable, "ops/lint.py"])
    if code != 0:
        problems.append(out)

    if args.full:
        code, out = run([sys.executable, "ops/self_test.py"])
        if code != 0:
            problems.append(out)

    if problems:
        print("DOCTOR REPORT")
        print("-------------")
        for p in problems:
            print(p)
        sys.exit(2)

    print("DOCTOR OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

def patch_ci_scripts_to_bootstrap_canon() -> None:
    # Patch ci_pack_smoke.py and self_test.py so they work in framework repo without canon/
    smoke = ROOT / "ops/ci_pack_smoke.py"
    if smoke.exists():
        txt = smoke.read_text(encoding="utf-8")
        if "canon_template" not in txt:
            # Overwrite with a safe version.
            write_text("ops/ci_pack_smoke.py", """\
#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

def main():
    tmp = Path(tempfile.mkdtemp(prefix="career_fw_ci_smoke_"))
    ws = tmp / ROOT.name
    shutil.copytree(ROOT, ws, dirs_exist_ok=True)

    # If canon missing, bootstrap from canon_template
    if not (ws / "canon").exists() and (ws / "canon_template").exists():
        shutil.copytree(ws / "canon_template", ws / "canon", dirs_exist_ok=True)

    # Make a small canon change
    p = ws / "canon/profile.md"
    if p.exists():
        p.write_text(p.read_text(encoding="utf-8") + "\\nCI_SMOKE_CHANGE\\n", encoding="utf-8", newline="\n")

    code, out = run([sys.executable, "ops/make_pack.py"], cwd=ws)
    if code != 0:
        print(out.strip())
        sys.exit(code)

    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    pack_path = None
    for ln in reversed(lines):
        if ln.endswith(".zip") and Path(ln).exists():
            pack_path = Path(ln).resolve()
            break
    if not pack_path:
        print("CI_SMOKE: no pack created")
        sys.exit(1)

    code, vout = run([sys.executable, "ops/validate_pack.py", str(pack_path)], cwd=ws)
    if code != 0:
        print(vout.strip())
        sys.exit(code)

    print("CI_SMOKE OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
""")

    st = ROOT / "ops/self_test.py"
    if st.exists():
        txt = st.read_text(encoding="utf-8")
        if "canon_template" not in txt:
            # Keep your existing self_test if already modern; otherwise overwrite with the v0.1.3+ version in your repo.
            # Minimal patch: bootstrap canon from canon_template right after workspace copy.
            # Safer to overwrite with a known-good version would be longer; we keep it minimal here.
            patched = txt
            marker = "if (ws / \".git\").exists():"
            if marker in patched:
                patched = patched.replace(
                    marker,
                    "        # Bootstrap canon from canon_template if missing\n        if not (ws / \"canon\").exists() and (ws / \"canon_template\").exists():\n            shutil.copytree(ws / \"canon_template\", ws / \"canon\", dirs_exist_ok=True)\n\n" + marker
                )
                st.write_text(patched, encoding="utf-8", newline="\n")

def main():
    patch_gitignore()

    # Ensure packs folders exist
    ensure_keep("packs/outgoing")
    ensure_keep("packs/incoming")
    ensure_keep("packs/archive")
    ensure_keep("packs/exports")
    ensure_keep("packs/archive/exports")

    patch_bundle_pack_to_outgoing()
    write_export_framework_py()
    write_export_newbie_pack_py()
    write_apply_latest_py()
    write_bat_launchers()
    write_newbie_docs()
    patch_pack_maintenance_for_exports()
    patch_doctor_to_autofix_hygiene()
    patch_ci_scripts_to_bootstrap_canon()

    # Create the two zips as outputs (ignored by git)
    # 1) framework export
    out1 = subprocess_run_py(["ops/export_framework.py"])
    # 2) newbie pack
    out2 = subprocess_run_py(["ops/export_newbie_pack.py"])

    print("PATCH OK")
    print(out1)
    print(out2)

def subprocess_run_py(rel_cmd):
    import subprocess
    r = subprocess.run([sys.executable] + rel_cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        return r.stdout.strip()
    return r.stdout.strip()

if __name__ == "__main__":
    main()