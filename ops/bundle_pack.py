#!/usr/bin/env python3
import datetime
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon"
MANIFEST_PATH = CANON / "pack_manifest.json"
META_PATH = CANON / "meta.yml"

ZIP_FIXED_TIME = (1980, 1, 1, 0, 0, 0)

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def bump_change_id(change_id: str) -> str:
    try:
        prefix, num = change_id.split("-")
        return f"{prefix}-{int(num)+1:04d}"
    except Exception:
        return "CHG-0001"

def load_meta() -> Dict:
    with META_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_meta(meta: Dict) -> None:
    lines = [
        f'schemaVersion: "{meta.get("schemaVersion","1")}"',
        f'frameworkVersion: "{meta.get("frameworkVersion","")}"',
        f'changeId: "{meta.get("changeId","CHG-0000")}"',
        f'baseChangeId: "{meta.get("baseChangeId","CHG-0000")}"',
        f'createdAt: "{meta.get("createdAt","")}"',
        f'lastPackCreatedAt: "{meta.get("lastPackCreatedAt","")}"',
        "",
    ]
    META_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")

def list_canon_files_for_baseline() -> List[Path]:
    files: List[Path] = []
    for p in CANON.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("canon/logs/archive/"):
            continue
        if rel == "canon/pack_manifest.json":
            continue
        files.append(p)
    return sorted(files, key=lambda x: x.relative_to(ROOT).as_posix())

def load_baseline_manifest() -> Dict:
    if not MANIFEST_PATH.exists():
        raise RuntimeError("Missing canon/pack_manifest.json baseline. Refusing to bundle the entire canon.")
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Invalid baseline manifest (canon/pack_manifest.json): {e}")
    if not isinstance(data, dict) or "files" not in data:
        raise RuntimeError("Baseline manifest missing required fields (files).")
    return data

def baseline_map(baseline: Dict) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for entry in baseline.get("files", []):
        if isinstance(entry, dict) and isinstance(entry.get("path"), str) and isinstance(entry.get("sha256"), str):
            m[entry["path"]] = entry["sha256"]
    return m

def compute_full_entries() -> List[Dict]:
    entries: List[Dict] = []
    for p in list_canon_files_for_baseline():
        rel = p.relative_to(ROOT).as_posix()
        data = p.read_bytes()
        entries.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data)})
    return entries

def canonical_manifest_sha(manifest: Dict) -> str:
    tmp = dict(manifest)
    tmp.pop("manifestSha256", None)
    canonical = json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(canonical)

def zip_write_bytes(z: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname)
    info.date_time = ZIP_FIXED_TIME
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)

def main() -> None:
    baseline = load_baseline_manifest()
    base_map = baseline_map(baseline)

    entries_pre = compute_full_entries()
    cur_map_pre = {e["path"]: e["sha256"] for e in entries_pre}

    changed_non_meta = [
        p for p, sha in cur_map_pre.items()
        if p != "canon/meta.yml" and base_map.get(p) != sha
    ]
    if not changed_non_meta:
        print("No canon changes detected (excluding meta). Nothing to bundle.")
        return

    meta = load_meta()
    base_change_id = meta.get("changeId", "CHG-0000")
    published_change_id = bump_change_id(base_change_id)
    created_at = utc_now()

    meta["baseChangeId"] = base_change_id
    meta["changeId"] = published_change_id
    meta["lastPackCreatedAt"] = created_at
    save_meta(meta)

    full_entries = compute_full_entries()
    cur_map = {e["path"]: e["sha256"] for e in full_entries}

    deleted = sorted([p for p in base_map.keys() if p not in cur_map])

    pack_files: List[str] = ["canon/meta.yml"]
    for path, sha in cur_map.items():
        if path == "canon/meta.yml":
            continue
        if base_map.get(path) != sha:
            pack_files.append(path)
    pack_files = sorted(list(set(pack_files)))

    manifest: Dict = {
        "schemaVersion": str(meta.get("schemaVersion", "")) if meta.get("schemaVersion") is not None else "",
        "frameworkVersion": str(meta.get("frameworkVersion", "")) if meta.get("frameworkVersion") is not None else "",
        "baseChangeId": base_change_id,
        "publishedChangeId": published_change_id,
        "createdAt": created_at,
        "packFiles": pack_files,
        "deleted": deleted,
        "files": full_entries,
    }
    manifest["manifestSha256"] = canonical_manifest_sha(manifest)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")

    safe_created = created_at.replace(":", "").replace("-", "")
    pack_name = f"canon_pack_{published_change_id}_{safe_created}.zip"
    out_path = ROOT / pack_name

    with zipfile.ZipFile(out_path, "w") as z:
        for path in pack_files:
            abs_path = ROOT / path
            if not abs_path.exists():
                raise RuntimeError(f"File missing while bundling: {path}")
            zip_write_bytes(z, path, abs_path.read_bytes())
        zip_write_bytes(z, "canon/pack_manifest.json", MANIFEST_PATH.read_bytes())

    print(str(out_path))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
