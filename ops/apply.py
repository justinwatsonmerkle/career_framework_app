#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon"
CONFLICTS = CANON / "conflicts"

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def safe_canon_target(rel_path: str) -> Path:
    if not rel_path.startswith("canon/"):
        raise ValueError(f"Refusing non-canon path: {rel_path}")
    target = (ROOT / rel_path).resolve()
    canon_root = CANON.resolve()
    if not str(target).startswith(str(canon_root) + os.sep) and target != canon_root:
        raise ValueError(f"Path traversal detected: {rel_path}")
    return target

def load_local_meta() -> Dict:
    with (CANON / "meta.yml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_local_manifest() -> Dict:
    p = CANON / "pack_manifest.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def manifest_sha_map(manifest: Dict) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for e in manifest.get("files", []):
        if isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("sha256"), str):
            m[e["path"]] = e["sha256"]
    return m

def validate_pack(pack_path: Path) -> Dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / "ops/validate_pack.py"), str(pack_path)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stdout.strip())

    with zipfile.ZipFile(pack_path, "r") as z:
        return json.loads(z.read("canon/pack_manifest.json").decode("utf-8"))

def capture_conflict_bundle(kind: str, manifest: Dict, local_change_id: str, pack_path: Path,
                           incoming_files: List[str], conflict_files: List[str]) -> Path:
    stamp = utc_now().replace(":", "").replace("-", "")
    root = CONFLICTS / stamp
    incoming_root = root / "incoming"
    local_root = root / "local"
    incoming_root.mkdir(parents=True, exist_ok=True)
    local_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(pack_path, "r") as z:
        for rel in incoming_files:
            safe_canon_target(rel)
            data = z.read(rel)
            out_in = (incoming_root / rel).resolve()
            out_in.parent.mkdir(parents=True, exist_ok=True)
            out_in.write_bytes(data)

            local_file = (ROOT / rel)
            out_local = (local_root / rel).resolve()
            out_local.parent.mkdir(parents=True, exist_ok=True)
            if local_file.exists():
                out_local.write_bytes(local_file.read_bytes())
            else:
                out_local.write_text("MISSING LOCALLY\n", encoding="utf-8", newline="\n")

    report_lines = [
        "# Conflict report",
        "",
        f"Reason: {kind}",
        "",
        f"Local changeId: {local_change_id}",
        f"Pack baseChangeId: {manifest.get('baseChangeId')}",
        f"Pack: {pack_path.name}",
        "",
        "Conflicted files:",
    ]
    for f in conflict_files:
        report_lines.append(f"- {f}")
    report_lines += [
        "",
        "Next steps:",
        "1) Compare incoming vs local under this folder.",
        "2) Resolve manually in canon/ (no deletion by omission).",
        "3) See docs/merge_guide.md.",
    ]
    (root / "conflict_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
    return root

def detect_file_level_conflicts(manifest: Dict, pack_path: Path) -> List[str]:
    local_manifest = load_local_manifest()
    baseline_sha = manifest_sha_map(local_manifest)

    conflicts: List[str] = []
    with zipfile.ZipFile(pack_path, "r") as z:
        for rel in manifest.get("packFiles", []):
            if not isinstance(rel, str):
                continue
            if rel == "canon/meta.yml":
                continue

            baseline = baseline_sha.get(rel)
            if not baseline:
                conflicts.append(rel)
                continue

            incoming = sha256_bytes(z.read(rel))
            local_path = ROOT / rel
            local = sha256_bytes(local_path.read_bytes()) if local_path.exists() else ""

            if local and local != baseline and incoming != baseline and incoming != local:
                conflicts.append(rel)

    return sorted(list(set(conflicts)))

def stage_and_swap(pack_path: Path, manifest: Dict) -> None:
    stamp = utc_now().replace(":", "").replace("-", "")
    stage_root = ROOT / f".tmp_apply_{stamp}"
    stage_canon = stage_root / "canon"
    backup = ROOT / f"canon__bak_{stamp}"

    if stage_root.exists():
        shutil.rmtree(stage_root)

    shutil.copytree(CANON, stage_canon)

    with zipfile.ZipFile(pack_path, "r") as z:
        pack_files: List[str] = list(manifest.get("packFiles", []))
        if "canon/pack_manifest.json" not in pack_files:
            pack_files.append("canon/pack_manifest.json")

        for rel in pack_files:
            if not isinstance(rel, str):
                raise RuntimeError("Invalid packFiles entry (not string).")
            safe_canon_target(rel)
            data = z.read(rel)

            stage_target = (stage_root / rel).resolve()
            canon_root = stage_canon.resolve()
            if not str(stage_target).startswith(str(canon_root) + os.sep) and stage_target != canon_root:
                raise RuntimeError(f"Stage path traversal detected: {rel}")

            stage_target.parent.mkdir(parents=True, exist_ok=True)
            stage_target.write_bytes(data)

    try:
        if backup.exists():
            shutil.rmtree(backup)
        os.rename(CANON, backup)
        os.rename(stage_canon, CANON)
        shutil.rmtree(stage_root, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
    except Exception as e:
        try:
            if backup.exists() and not CANON.exists():
                os.rename(backup, CANON)
        except Exception:
            pass
        raise RuntimeError(f"Apply failed during swap: {e}")

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python ops/apply.py path/to/pack.zip")
        sys.exit(1)

    pack_path = Path(sys.argv[1]).resolve()
    if not pack_path.exists():
        print(f"Pack not found: {pack_path}")
        sys.exit(1)

    manifest = validate_pack(pack_path)

    local_meta = load_local_meta()
    local_change_id = str(local_meta.get("changeId", "CHG-0000"))
    pack_base = str(manifest.get("baseChangeId", ""))

    if pack_base and pack_base != local_change_id:
        incoming_files = sorted(list(set([p for p in manifest.get("packFiles", []) if isinstance(p, str)] + ["canon/pack_manifest.json"])))
        conflict_root = capture_conflict_bundle(
            kind="baseChangeId mismatch",
            manifest=manifest,
            local_change_id=local_change_id,
            pack_path=pack_path,
            incoming_files=incoming_files,
            conflict_files=incoming_files,
        )
        print("BASECHANGEID MISMATCH - NOT APPLIED")
        print(f"Conflict captured to: {conflict_root.as_posix()}")
        sys.exit(2)

    file_conflicts = detect_file_level_conflicts(manifest, pack_path)
    if file_conflicts:
        incoming_files = sorted(list(set([p for p in manifest.get("packFiles", []) if isinstance(p, str)] + ["canon/pack_manifest.json"])))
        conflict_root = capture_conflict_bundle(
            kind="file-level conflicts",
            manifest=manifest,
            local_change_id=local_change_id,
            pack_path=pack_path,
            incoming_files=incoming_files,
            conflict_files=file_conflicts,
        )
        print("FILE CONFLICTS - NOT APPLIED")
        print(f"Conflict captured to: {conflict_root.as_posix()}")
        sys.exit(3)

    stage_and_swap(pack_path, manifest)
    print("Pack applied.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
