# SOP - Career Development Framework

This SOP is the operating contract for assistants and tooling.

## 1) Principles

1. Durable state lives outside chat in canon artefacts.
2. Chats are disposable. Canon is durable.
3. One mode per session.
4. Controlled publishing: no canon changes are written unless CHECKPOINT or WRAP_UP is explicitly invoked.
5. Change safety: default non-destructive (omission is not deletion).
6. Share the framework and blank templates; keep personal canon private.

## 2) Folder boundaries and precedence

- core/      : shared framework kit (read-only to end users)
- overlays/  : user-owned tweaks that override core defaults
- canon/     : user-owned durable state (private by default)
- ops/       : helper scripts (lint, pack, apply, logs)

Precedence when resolving configuration or templates:
1) overlays/
2) canon/ (user state)
3) core/ defaults/templates

Framework upgrades MUST NOT overwrite anything in overlays/ or canon/.
Upgrades are additive: add new files; version templates rather than replacing user-owned files.

## 3) Session operating rules (assistant behaviour)

- Select exactly one Mode Card from core/framework/mode_cards/ at session start.
- During the session, the assistant may:
  - reason, explore, ask questions, draft text in-chat
  - stage proposed canon changes internally (ADD/REFINE/REPLACE/etc)
  - capture cross-mode implications as backlog/evidence/assumption items (staged)
- The assistant MUST NOT write or output any updated canon files unless:
  - user explicitly says: CHECKPOINT or WRAP_UP

### 3.1 Cross-mode capture (routing metadata)

When anything arises that belongs to another mode, stage an item into:
- canon/backlog.md (follow-ups)
- canon/assumptions.md (NEEDS_CONFIRMATION)
- canon/evidence_register.md (evidence needed)

Every backlog item MUST include:
- TargetMode, Domain, Type, Priority, CreatedAt, SourceSessionId

Default: do not interrupt the flow unless the risk is high (see 3.3).

### 3.2 Change interpretation (safe defaults)

Each staged change has:
- intent: ADD | CONFIRM | REFINE | DEPRECATE | REPLACE | CONTRADICT | UNKNOWN
- confidence: 0.0 to 1.0
- risk: LOW | MEDIUM | HIGH
- target artefact + field(s)

Rules:
- Omission is not deletion.
- Destructive changes (DEPRECATE/REPLACE) only apply when intent is explicit OR confirmed at publish time.
- If unclear, keep prior canon intact, add NEEDS_CONFIRMATION to assumptions, and add a backlog item.

### 3.3 Ambiguity triggers and interruption policy

Trigger phrases (examples): new, now, changed, updated, instead, no longer, stopped, dropped,
handed over, replaced, everything, complete list.

Interruption policy: hybrid
- Interrupt immediately only for HIGH-risk destructive edits.
- Otherwise, queue items into a Decision Queue to be resolved at CHECKPOINT/WRAP_UP.

## 4) CHECKPOINT and WRAP_UP outputs

On CHECKPOINT or WRAP_UP, the assistant produces:
1) A zip file containing only the updated canon artefacts (full files, correct paths).
2) A single code block containing publish metadata:
   - BaseCanonPack (path/name if known)
   - BaseChangeId
   - PublishedChangeId
   - ChangedCanonFiles
   - UTC_PublishedAt
   - CommitBranch
   - CommitMessage
   - PRTitle
   - PRDescription

Differences:
- CHECKPOINT: minimal save point (no polish required).
- WRAP_UP: publish-ready; include a short recap plus any unresolved Decision Queue items.

The assistant must NOT paste file contents in chat when it produces the zip.
It must output full files inside the zip, preserving filenames exactly.

## 5) Packs, manifests, conflicts

A pack must include:
- canon/meta.yml (contains changeId and baseChangeId)
- canon/pack_manifest.json (list of files, sha256, baseChangeId)
- only the canon files that changed in this session

Conflict rule:
- When applying a pack, if pack.baseChangeId != local.changeId:
  - do not silently merge
  - surface an explicit merge workflow and ask the user to choose the truth
  - keep both versions if needed (side-by-side with timestamps)

## 6) Logging (audit without bloat)

- Tier A: per-session log under canon/logs/sessions/
- Tier B: rolling log under canon/logs/rolling_log.md (window is settings.logging.rollingWindowDays; default 60)
- Tier C: cold archive under canon/logs/archive/ (excluded from packs)

Packs should include:
- rolling_log.md
- optionally the current session log
- never the full archive

## 7) Text hygiene and lint

- Prefer plain ASCII punctuation.
- Avoid smart quotes, em/en dashes, non-breaking spaces.
- Validate YAML/JSON parses.
- Guard folder boundaries (no writes to core/ during user sessions).
