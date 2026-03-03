#!/usr/bin/env python3
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.settings import load_settings  # noqa: E402

SESS = ROOT / "canon/logs/sessions"
ROLL = ROOT / "canon/logs/rolling_log.md"
ARCH = ROOT / "canon/logs/archive"

def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0)

def _get_window_days(settings) -> int:
    try:
        return int(settings.get("logging", {}).get("rollingWindowDays", 60))
    except Exception:
        return 60

def main():
    settings = load_settings()
    window_days = _get_window_days(settings)

    now = utc_now()
    cutoff = now - datetime.timedelta(days=window_days)

    lines = [f"# Rolling log (last {window_days} days)", ""]
    for p in sorted(SESS.glob("*.md")):
        ts = None
        stem = p.stem
        if stem.startswith("session_"):
            raw = stem.replace("session_", "").replace("Z", "").replace("_", ":")
            try:
                ts = datetime.datetime.fromisoformat(raw)
            except Exception:
                ts = None

        content = p.read_text(encoding="utf-8").strip()

        if ts and ts < cutoff:
            ARCH.mkdir(parents=True, exist_ok=True)
            p.rename(ARCH / p.name)
            continue

        if content:
            lines.append(f"## {p.name}")
            lines.append(content)
            lines.append("")

    ROLL.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("Logs compacted.")

if __name__ == "__main__":
    main()
