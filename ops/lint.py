\
#!/usr/bin/env python3
import os
import sys
import json
import yaml  # type: ignore

SMART_CHARS = {
    "\u2018": "LEFT SINGLE QUOTE",
    "\u2019": "RIGHT SINGLE QUOTE",
    "\u201C": "LEFT DOUBLE QUOTE",
    "\u201D": "RIGHT DOUBLE QUOTE",
    "\u2013": "EN DASH",
    "\u2014": "EM DASH",
    "\u00A0": "NO-BREAK SPACE",
    "\u2026": "ELLIPSIS",
}

ALLOWED_EXT = {".md", ".yml", ".yaml", ".json", ".py", ".txt"}

def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        # skip archives and zips
        if "canon/logs/archive" in dirpath.replace("\\", "/"):
            continue
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if os.path.splitext(fn)[1].lower() in ALLOWED_EXT:
                yield p

def check_text(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return [f"{path}: not utf-8 ({e})"]
    issues = []
    for ch, name in SMART_CHARS.items():
        if ch in text:
            issues.append(f"{path}: contains {name} ({repr(ch)})")
    # guard: tabs
    if "\t" in text:
        issues.append(f"{path}: contains TAB characters")
    return issues

def check_yaml_json(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in {".yml", ".yaml"}:
        with open(path, "r", encoding="utf-8") as f:
            try:
                yaml.safe_load(f)
            except Exception as e:
                return [f"{path}: YAML parse error: {e}"]
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            try:
                json.load(f)
            except Exception as e:
                return [f"{path}: JSON parse error: {e}"]
    return []

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    issues = []
    for p in iter_files(root):
        issues.extend(check_text(p))
        issues.extend(check_yaml_json(p))

    # boundary rule: user sessions must not modify core/ (lint only warns here)
    # In practice, Git hooks can enforce this. We keep it informational.
    if issues:
        print("LINT FAILED")
        for i in issues:
            print("-", i)
        sys.exit(1)
    print("LINT OK")

if __name__ == "__main__":
    try:
        import yaml  # noqa: F401
    except Exception:
        print("Missing dependency: pyyaml. Install with: pip install pyyaml")
        sys.exit(2)
    main()
