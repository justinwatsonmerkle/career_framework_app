#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def list_zip(zpath: Path):
    with zipfile.ZipFile(zpath, "r") as z:
        return sorted([i.filename for i in z.infolist() if not i.is_dir()])

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

def make_copy_workspace() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="career_fw_selftest_"))
    shutil.copytree(ROOT, tmp / ROOT.name, dirs_exist_ok=True)
    return tmp / ROOT.name

def write_append(path: Path, text: str):
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8", newline="\n")

def parse_pack_path(output: str) -> Path:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if ln.endswith(".zip") and Path(ln).exists():
            return Path(ln).resolve()
    raise RuntimeError("No pack path found in output")

def corrupt_zip_file(zpath: Path, target: str):
    with zipfile.ZipFile(zpath, "r") as zin:
        entries = {i.filename: zin.read(i.filename) for i in zin.infolist() if not i.is_dir()}
    if target not in entries:
        raise RuntimeError(f"Target not found in zip: {target}")
    entries[target] = entries[target] + b"X"
    tmp = zpath.parent / (zpath.stem + "_tmp.zip")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)
    tmp.replace(zpath)

def add_traversal_entry(zpath: Path):
    tmp = zpath.parent / (zpath.stem + "_trav.zip")
    shutil.copyfile(zpath, tmp)
    with zipfile.ZipFile(tmp, "a", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("canon/../../evil.txt", b"EVIL")
    return tmp

def sha256_text(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def make_minimal_manifest(pack_files, base_change_id, published_change_id, created_at, sha_map):
    files = []
    for p in pack_files:
        files.append({"path": p, "sha256": sha_map[p], "bytes": 0})
    manifest = {
        "schemaVersion": "1",
        "frameworkVersion": "0.1.2",
        "baseChangeId": base_change_id,
        "publishedChangeId": published_change_id,
        "createdAt": created_at,
        "packFiles": pack_files,
        "deleted": [],
        "files": files,
    }
    canonical = json.dumps({k: v for k, v in manifest.items() if k != "manifestSha256"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    import hashlib
    manifest["manifestSha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest

def get_change_id(ws: Path) -> str:
    meta = (ws / "canon/meta.yml").read_text(encoding="utf-8")
    for ln in meta.splitlines():
        if ln.startswith("changeId:"):
            return ln.split('"')[1]
    return "CHG-0000"

def build_file_conflict_pack(ws: Path, base_change_id: str) -> Path:
    # Create a pack that changes canon/profile.md differently from local baseline.
    profile = ws / "canon/profile.md"
    meta = ws / "canon/meta.yml"

    incoming_profile = profile.read_text(encoding="utf-8") + "\nINCOMING_CHANGE\n"
    incoming_meta = meta.read_text(encoding="utf-8")

    created_at = "2000-01-01T00:00:00Z"
    pack_files = ["canon/meta.yml", "canon/profile.md"]

    sha_map = {
        "canon/profile.md": sha256_text(incoming_profile),
        "canon/meta.yml": sha256_text(incoming_meta),
    }

    manifest = make_minimal_manifest(
        pack_files=pack_files,
        base_change_id=base_change_id,
        published_change_id=base_change_id,
        created_at=created_at,
        sha_map=sha_map,
    )

    out = ws / "incoming_file_conflict_pack.zip"
    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("canon/meta.yml", incoming_meta.encode("utf-8"))
        z.writestr("canon/profile.md", incoming_profile.encode("utf-8"))
        z.writestr("canon/pack_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=True).encode("utf-8"))

    return out

def main():
    ws = make_copy_workspace()
    if (ws / ".git").exists():
        shutil.rmtree(ws / ".git")

    # 1) Pack minimality without Git
    write_append(ws / "canon/profile.md", "\nSELFTEST_LOCAL_CHANGE\n")

    r = run([sys.executable, "ops/make_pack.py"], cwd=ws)
    assert_true(r.returncode == 0, f"make_pack failed:\n{r.stdout}")
    pack_path = parse_pack_path(r.stdout)
    assert_true(pack_path.exists(), "pack not created")

    files = list_zip(pack_path)
    assert_true("canon/meta.yml" in files, "meta.yml missing from pack")
    assert_true("canon/pack_manifest.json" in files, "pack_manifest.json missing from pack")
    assert_true("canon/profile.md" in files, "changed file missing from pack")
    assert_true("canon/goals.md" not in files, "pack incorrectly includes canon/goals.md")
    assert_true("canon/plans.md" not in files, "pack incorrectly includes canon/plans.md")

    # 2) validate_pack passes
    r2 = run([sys.executable, "ops/validate_pack.py", str(pack_path)], cwd=ws)
    assert_true(r2.returncode == 0, f"validate_pack failed:\n{r2.stdout}")

    # 3) Traversal rejection (validate fails before apply writes)
    trav_pack = add_traversal_entry(pack_path)
    r3 = run([sys.executable, "ops/apply.py", str(trav_pack)], cwd=ws)
    assert_true(r3.returncode != 0, "apply did not reject traversal pack")

    # 4) Checksum mismatch rejection
    bad_pack = ws / "bad_checksum.zip"
    shutil.copyfile(pack_path, bad_pack)
    corrupt_zip_file(bad_pack, "canon/profile.md")
    r4 = run([sys.executable, "ops/apply.py", str(bad_pack)], cwd=ws)
    assert_true(r4.returncode != 0, "apply did not reject checksum mismatch")

    # 5) Conflict capture: baseChangeId mismatch
    # Applying the pack to the same workspace should mismatch because local changeId has advanced.
    r5 = run([sys.executable, "ops/apply.py", str(pack_path)], cwd=ws)
    assert_true(r5.returncode == 2, f"expected baseChangeId conflict exit 2, got {r5.returncode}\n{r5.stdout}")

    conflicts_dir = ws / "canon/conflicts"
    assert_true(conflicts_dir.exists(), "conflicts directory not created")
    latest = sorted([p for p in conflicts_dir.iterdir() if p.is_dir()])[-1]
    assert_true((latest / "conflict_report.md").exists(), "conflict_report.md missing")
    assert_true((latest / "incoming/canon/profile.md").exists(), "incoming profile missing")
    assert_true((latest / "local/canon/profile.md").exists(), "local profile missing")

    # 6) Conflict capture: file-level conflict
    # Create incoming pack with baseChangeId matching current local changeId.
    local_change_id = get_change_id(ws)

    # Diverge locally from baseline
    write_append(ws / "canon/profile.md", "\nLOCAL_DIVERGENCE\n")

    incoming_pack = build_file_conflict_pack(ws, base_change_id=local_change_id)
    r6 = run([sys.executable, "ops/apply.py", str(incoming_pack)], cwd=ws)
    assert_true(r6.returncode == 3, f"expected file conflict exit 3, got {r6.returncode}\n{r6.stdout}")

    latest2 = sorted([p for p in conflicts_dir.iterdir() if p.is_dir()])[-1]
    assert_true((latest2 / "conflict_report.md").exists(), "conflict_report.md missing (file-level)")
    assert_true((latest2 / "incoming/canon/profile.md").exists(), "incoming profile missing (file-level)")
    assert_true((latest2 / "local/canon/profile.md").exists(), "local profile missing (file-level)")

    print("SELFTEST OK")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SELFTEST FAIL: {e}")
        sys.exit(1)
