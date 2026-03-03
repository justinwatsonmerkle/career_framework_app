# Merge guide (conflicts)

A conflict is captured when:
- baseChangeId mismatch (pack is from a different canon baseline), or
- file-level conflicts are detected (both local and incoming diverged from the same baseline).

What happens
- Apply refuses to apply the pack.
- It captures BOTH versions under:
  - canon/conflicts/<timestamp>/incoming/<relative paths under canon/>
  - canon/conflicts/<timestamp>/local/<relative paths under canon/>
- It writes:
  - canon/conflicts/<timestamp>/conflict_report.md

Safe approach
1) Do not overwrite anything.
2) Compare incoming vs local and choose the truth explicitly.
3) Resolve in canon/ and then publish a new pack.

Practical workflow
- Open conflict_report.md and review the listed files.
- Compare the captured versions.
- Make edits in canon/.
- Then run:
  ```bash
  python ops/make_pack.py
  ```
