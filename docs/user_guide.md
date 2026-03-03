# User guide

## Golden Path (recommended)

1) ChatGPT session
   - Work in one mode.
   - When you want to save durable state, say CHECKPOINT or WRAP_UP.
   - The assistant returns an incoming pack zip (canon-only changes).

2) Local apply
   ```bash
   python ops/apply.py path/to/incoming_pack.zip
   ```
   - Validates the pack (paths, checksums, mandatory files) before writing anything.
   - Applies atomically (stage then swap).
   - On conflicts, writes a bundle under canon/conflicts/<timestamp>/ and stops.

3) Commit and push (private repo)
   - Commit changes in canon/ and any framework changes.
   - Push. CI runs lint, privacy guard, and self-tests.

4) Optional: produce the next resume pack
   ```bash
   python ops/make_pack.py
   ```
   - Runs lint, compacts logs, builds a deterministic minimal pack, validates it.
   - Prints the output pack path.

## Default repo model (private)

- Keep the repository private.
- Track canon/ in the private repo (diffs, rollbacks, CI).

Safe sharing is mechanical:
```bash
python ops/export_framework.py
```
This produces a framework-only zip (no canon/, no overlays/).

## Scripts overview

- Apply incoming pack:
  - ops/apply.py

- Make resume pack:
  - ops/make_pack.py

- Validate a pack:
  - ops/validate_pack.py

- Export framework only:
  - ops/export_framework.py

## Troubleshooting

- If lint fails, fix smart punctuation or encoding issues and rerun:
  ```bash
  python ops/lint.py
  ```

- If apply reports conflicts:
  - Review canon/conflicts/<timestamp>/conflict_report.md
  - Follow docs/merge_guide.md
