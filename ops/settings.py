#!/usr/bin/env python3
# Settings loader with precedence:
#   overlays/ > canon/ > core defaults
#
# All files are expected to be UTF-8 YAML.
#
# If canon/settings.yml is missing, this module bootstraps it from core defaults.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parent.parent

def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def bootstrap_settings_if_missing() -> None:
    core_defaults = ROOT / "core/framework/defaults/settings.default.yml"
    canon_settings = ROOT / "canon/settings.yml"
    if canon_settings.exists():
        return
    canon_settings.parent.mkdir(parents=True, exist_ok=True)
    canon_settings.write_text(core_defaults.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

def load_settings() -> Dict[str, Any]:
    core_defaults = ROOT / "core/framework/defaults/settings.default.yml"
    overlays_settings = ROOT / "overlays/settings.override.yml"
    canon_settings = ROOT / "canon/settings.yml"

    bootstrap_settings_if_missing()

    settings = _read_yaml(core_defaults)
    settings = _deep_merge(settings, _read_yaml(canon_settings))
    settings = _deep_merge(settings, _read_yaml(overlays_settings))
    return settings
