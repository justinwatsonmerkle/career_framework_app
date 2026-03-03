# Maintainer guide (framework owners)

## Upgrade safety contract

- Never overwrite user-owned overlays/ or canon/.
- Upgrades are additive (new files, new versions).
- If templates must change, ship a new version (do not replace user files).

Versioning
- core/framework/versions/framework_version.yml is authoritative.

## Default private repo model

- Track canon/ in the private repo (diffs, rollbacks, CI).
- Do not publish canon/ in a public repo.
- Share via:
  ```bash
  python ops/export_framework.py
  ```

## Packs (checksum-based, no Git required)

- canon/pack_manifest.json is the baseline snapshot of canon state (hashes for canon files).
- ops/make_pack.py runs:
  - ops/lint.py
  - ops/compact_logs.py
  - ops/bundle_pack.py
  - ops/validate_pack.py
- ops/apply.py runs ops/validate_pack.py before writing anything and applies atomically.

## CI expectations

- Lint must pass (UTF-8, no smart punctuation, valid YAML and JSON).
- Public repo guard fails if canon/ exists or is tracked when repo visibility is public.
- Self-test validates pack minimality and apply safety.

## Regression checklist (minimal)

- Mode cards reference real canon templates and use Router-first guidance.
- validate_pack rejects traversal and checksum mismatch.
- bundle_pack creates minimal packs and never bundles the entire canon without a baseline.
- apply captures conflicts under canon/conflicts/<timestamp>/ with incoming and local versions.
