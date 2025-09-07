"""Output persistence utilities for PM Team runs.

Separation of concerns:
- This module knows ONLY about serialization & filesystem layout.
- It does NOT construct domain objects (plan/release/etc.) or invoke LLMs.
- Public function: persist_run(result, autogen_raw, initiative, base_dir)

Directory layout (default base: autogen_pm_team/outputs):
  outputs/
    20250907_153012_ai_driven_real_time_anomaly_detection/
        plan.json
        release.json
        metrics.json
        stakeholder_summary.txt
        aggregate_risk.txt (single line numeric)
        blockers.txt (one blocker per line if any)
        autogen/
            planner_raw.txt
            release_raw.txt
            stakeholder_raw.txt

An environment variable PM_TEAM_OUTPUT_ROOT can override the base output directory.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import json
import os
import re
from datetime import datetime, UTC

SANITIZE_RE = re.compile(r"[^a-z0-9_\-]+")


def _slug(text: str, max_len: int = 60) -> str:
    lower = text.strip().lower().replace(" ", "_")
    cleaned = SANITIZE_RE.sub("", lower)
    return cleaned[:max_len] or "run"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_base_output_dir(default: Optional[Path] = None) -> Path:
    override = os.getenv("PM_TEAM_OUTPUT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return default or Path(__file__).resolve().parents[1] / "outputs"


def persist_run(result: Dict[str, Any], autogen_raw: Optional[Dict[str, Any]], initiative: str, base_dir: Optional[Path] = None) -> Path:
    base = get_base_output_dir(base_dir)
    run_dir = base / f"{_timestamp()}_{_slug(initiative)}"
    _ensure_dir(run_dir)

    # Core artifacts
    plan = result.get("plan")
    release = result.get("release")
    metrics = result.get("metrics")
    agg_risk = result.get("aggregate_risk_score") or plan.get("aggregate_risk_score") if plan else None

    if plan:
        (run_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        blockers = plan.get("blockers", [])
        if blockers:
            (run_dir / "blockers.txt").write_text("\n".join(blockers))
    if release:
        (run_dir / "release.json").write_text(json.dumps(release, indent=2, ensure_ascii=False))
    if metrics:
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    if agg_risk is not None:
        (run_dir / "aggregate_risk.txt").write_text(str(agg_risk))

    stakeholder_summary = result.get("stakeholder_summary")
    if stakeholder_summary:
        (run_dir / "stakeholder_summary.txt").write_text(stakeholder_summary)

    # Raw Autogen outputs
    if autogen_raw:
        auto_dir = _ensure_dir(run_dir / "autogen")
        for key, val in autogen_raw.items():
            text = val if isinstance(val, str) else str(val)
            (auto_dir / f"{key}_raw.txt").write_text(text)

    # Write manifest
    manifest = {
        "initiative": initiative,
        "created_at": datetime.now(UTC).isoformat(),
        "files": sorted([p.name for p in run_dir.iterdir() if p.is_file()]),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    return run_dir

__all__ = ["persist_run", "get_base_output_dir"]