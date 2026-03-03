#!/usr/bin/env python3
import hashlib
import json
import posixpath
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, List, Set

MANDATORY = {"canon/meta.yml", "canon/pack_manifest.json"}

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical_manifest_sha(manifest: Dict) -> str:
    tmp = dict(manifest)
    tmp.pop("manifestSha256", None)
    canonical = json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(canonical)

def list_zip_files(z: zipfile.ZipFile) -> List[str]:
    return sorted([i.filename for i in z.infolist() if not i.is_dir()])

def is_safe_canon_path(p: str) -> bool:
    # Reject windows separators and drive-like paths
    if "\\" in p:
        return False
    if ":" in p:
        return False
    if not p.startswith("canon/"):
        return False
    norm = posixpath.normpath(p)
    if not norm.startswith("canon/"):
        return False
    parts = PurePosixPath(norm).parts
    if ".." in parts:
        return False
    if PurePosixPath(norm).is_absolute():
        return False
    return True

def fail(msg: str) -> None:
    print(f"INVALID PACK: {msg}")
    sys.exit(2)

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python ops/validate_pack.py path/to/pack.zip")
        sys.exit(1)

    pack_path = Path(sys.argv[1]).resolve()
    if not pack_path.exists():
        print(f"Pack not found: {pack_path}")
        sys.exit(1)

    with zipfile.ZipFile(pack_path, "r") as z:
        files = list_zip_files(z)

        for f in files:
            if not is_safe_canon_path(f):
                fail(f"unsafe path: {f}")

        for req in sorted(MANDATORY):
            if req not in files:
                fail(f"mandatory file missing: {req}")

        try:
            manifest_raw = z.read("canon/pack_manifest.json")
        except Exception as e:
            fail(f"cannot read canon/pack_manifest.json: {e}")

        try:
            manifest = json.loads(manifest_raw.decode("utf-8"))
        except Exception as e:
            fail(f"manifest JSON invalid UTF-8 or parse error: {e}")

        if not isinstance(manifest, dict):
            fail("manifest is not an object")

        required_keys = ["baseChangeId", "publishedChangeId", "createdAt", "files", "packFiles", "manifestSha256"]
        for k in required_keys:
            if k not in manifest:
                fail(f"manifest missing required field: {k}")

        if manifest.get("manifestSha256") != canonical_manifest_sha(manifest):
            fail("manifestSha256 mismatch (manifest integrity failure)")

        pack_files = manifest.get("packFiles")
        if not isinstance(pack_files, list):
            fail("manifest.packFiles is not a list")

        pack_files = [p for p in pack_files if isinstance(p, str)]

        if "canon/meta.yml" not in pack_files:
            fail("manifest.packFiles missing canon/meta.yml")

        for p in pack_files:
            if not is_safe_canon_path(p):
                fail(f"manifest.packFiles contains unsafe path: {p}")

        zip_set: Set[str] = set(files)
        zip_minus_manifest = set([p for p in zip_set if p != "canon/pack_manifest.json"])
        pack_set = set(pack_files)

        if pack_set != zip_minus_manifest:
            extra_in_zip = sorted(list(zip_minus_manifest - pack_set))
            extra_in_manifest = sorted(list(pack_set - zip_minus_manifest))
            if extra_in_zip:
                fail(f"zip contains files not listed in manifest.packFiles: {extra_in_zip}")
            if extra_in_manifest:
                fail(f"manifest.packFiles lists files not present in zip: {extra_in_manifest}")
            fail("packFiles mismatch")

        file_entries = manifest.get("files")
        if not isinstance(file_entries, list):
            fail("manifest.files is not a list")

        sha_map: Dict[str, str] = {}
        for e in file_entries:
            if isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("sha256"), str):
                sha_map[e["path"]] = e["sha256"]

        for p in sorted(pack_set):
            if p not in sha_map:
                fail(f"manifest.files missing sha256 for pack file: {p}")

        for p in sorted(pack_set):
            data = z.read(p)
            if sha256_bytes(data) != sha_map[p]:
                fail(f"checksum mismatch for {p}")

    print("VALID PACK")
    sys.exit(0)

if __name__ == "__main__":
    main()
