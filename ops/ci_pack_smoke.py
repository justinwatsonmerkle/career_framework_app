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
        p.write_text(p.read_text(encoding="utf-8") + "\nCI_SMOKE_CHANGE\n", encoding="utf-8", newline="\n")

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
