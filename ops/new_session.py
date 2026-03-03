\
#!/usr/bin/env python3
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESS_DIR = ROOT / "canon/logs/sessions"

def utc_stamp():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def main():
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    safe = stamp.replace(":","_")
    p = SESS_DIR / f"session_{safe}.md"
    if not p.exists():
        p.write_text(f"# Session log {stamp}\n\n- TODO\n", encoding="utf-8", newline="\n")
    print(p.as_posix())

if __name__ == "__main__":
    main()
