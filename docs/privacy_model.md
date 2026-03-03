# Privacy model

Default operating model
- Use one private personal repository for day-to-day work.
- Track canon/ in that private repo so diffs, rollbacks, and CI checks work.

Non-negotiable rule
- canon/ is personal state. Do not publish canon/ in a public repository.

Safe sharing (mechanical)
- Share only the framework code and templates via a mechanical export:
  ```bash
  python ops/export_framework.py
  ```
- The export zip contains only:
  - core/
  - ops/
  - docs/
  - canon_template/
- It explicitly excludes:
  - canon/
  - overlays/

Why this works
- You can collaborate on framework improvements without exposing personal state.
- You can import framework updates into your private repo without overwriting canon/.
