#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd):
    r = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

def main() -> None:
    code, out = run([sys.executable, "ops/lint.py"])
    if code != 0:
        print(out.strip())
        sys.exit(code)

    code, out = run([sys.executable, "ops/compact_logs.py"])
    if code != 0:
        print(out.strip())
        sys.exit(code)

    code, out = run([sys.executable, "ops/bundle_pack.py"])
    if code != 0:
        print(out.strip())
        sys.exit(code)

    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        print("No output from bundle_pack.")
        sys.exit(1)

    last = lines[-1].strip()
    if not last.endswith(".zip") or not Path(last).exists():
        print(out.strip())
        sys.exit(0)

    pack_path = Path(last).resolve()
    code, vout = run([sys.executable, "ops/validate_pack.py", str(pack_path)])
    if code != 0:
        print(vout.strip())
        sys.exit(code)

    print(str(pack_path))
    sys.exit(0)

if __name__ == "__main__":
    main()
