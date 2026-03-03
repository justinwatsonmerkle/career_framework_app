#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, cwd):
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout = (p.stdout or "").strip()
    stderr = (p.stderr or "").strip()
    return p.returncode, stdout, stderr

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

    code, out, err = run([sys.executable, "ops/make_pack.py"], cwd=ws)
    if code != 0:
        print("CI_SMOKE: make_pack failed")
        print(f"cwd: {ws}")
        print(f"cmd: {sys.executable} ops/make_pack.py")
        print(f"returncode: {code}")
        print("stdout:")
        print(out if out else "<empty>")
        print("stderr:")
        print(err if err else "<empty>")
        sys.exit(code)

    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    pack_path = None
    for ln in reversed(lines):
        if ln.endswith(".zip") and Path(ln).exists():
            pack_path = Path(ln).resolve()
            break
    if not pack_path:
        print("CI_SMOKE: no pack created")
        print("stdout:")
        print(out if out else "<empty>")
        print("stderr:")
        print(err if err else "<empty>")
        sys.exit(1)

    code, vout, verr = run([sys.executable, "ops/validate_pack.py", str(pack_path)], cwd=ws)
    if code != 0:
        print("CI_SMOKE: validate_pack failed")
        print(f"cwd: {ws}")
        print(f"cmd: {sys.executable} ops/validate_pack.py {pack_path}")
        print(f"returncode: {code}")
        print("stdout:")
        print(vout if vout else "<empty>")
        print("stderr:")
        print(verr if verr else "<empty>")
        sys.exit(code)

    print("CI_SMOKE OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
