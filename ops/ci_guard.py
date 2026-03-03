#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.request

def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

def is_canon_tracked():
    code, out = run(["git", "ls-files", "canon"])
    if code != 0:
        return False
    return any(line.strip() for line in out.splitlines())

def canon_exists():
    return os.path.isdir("canon")

def get_visibility_from_env():
    v = (os.environ.get("REPO_VISIBILITY") or os.environ.get("REPOSITORY_VISIBILITY") or "").strip().lower()
    if v in ("public", "private", "internal"):
        return v
    return ""

def get_visibility_from_github_api():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not token or not repo:
        return ""
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and isinstance(data.get("visibility"), str):
                return data["visibility"].strip().lower()
    except Exception:
        return ""
    return ""

def main():
    visibility = get_visibility_from_env() or get_visibility_from_github_api()

    if not visibility:
        print("CI_GUARD: visibility unknown, skipping public repo canon guard.")
        sys.exit(0)

    if visibility == "public":
        if canon_exists() or is_canon_tracked():
            print("CI_GUARD FAIL: repo is public and canon/ exists or is tracked.")
            print("Fix: remove canon/ from the public repo and share via ops/export_framework.py instead.")
            sys.exit(2)

    print(f"CI_GUARD OK: visibility={visibility}")
    sys.exit(0)

if __name__ == "__main__":
    main()
