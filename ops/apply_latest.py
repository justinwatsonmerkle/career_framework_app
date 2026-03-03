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
