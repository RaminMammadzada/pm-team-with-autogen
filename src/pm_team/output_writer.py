from __future__ import annotations
"""Output persistence utilities.

Default location: project root `outputs/` (created automatically if absent).
Override with environment variable: `PM_TEAM_OUTPUT_ROOT`.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
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
        p = Path(override).expanduser().resolve()
        _ensure_dir(p)
        return p
    root = Path(__file__).resolve().parents[2]
    out = default or root / "outputs"
    _ensure_dir(out)
    return out


def _prune_old_runs(project_path: Path, keep: int):
    if keep is None:
        return
    run_dirs: List[Path] = [d for d in project_path.iterdir() if d.is_dir()]
    # sort by name (timestamp prefix ensures chronological order)
    run_dirs.sort(key=lambda p: p.name)
    excess = len(run_dirs) - keep
    for d in run_dirs[:excess]:
        try:
            for sub in d.rglob('*'):
                if sub.is_file():
                    sub.unlink(missing_ok=True)  # type: ignore[arg-type]
            for sub in sorted([p for p in d.rglob('*') if p.is_dir()], reverse=True):
                sub.rmdir()
            d.rmdir()
        except Exception:
            pass


def persist_run(result: Dict[str, Any], autogen_raw: Optional[Dict[str, Any]], initiative: str, base_dir: Optional[Path] = None, project: str = "default", max_runs: Optional[int] = None) -> Path:
    # Projects now create subdirectories under outputs/<project_slug>
    base_root = get_base_output_dir(base_dir)
    from .projects import project_dir, increment_run_counter  # local import to avoid circular
    proj_dir = project_dir(project)
    _ensure_dir(proj_dir)
    run_dir = proj_dir / f"{_timestamp()}_{_slug(initiative)}"
    _ensure_dir(run_dir)

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

    if autogen_raw:
        auto_dir = _ensure_dir(run_dir / "autogen")
        for key, val in autogen_raw.items():
            text = val if isinstance(val, str) else str(val)
            (auto_dir / f"{key}_raw.txt").write_text(text)

    manifest = {
        "initiative": initiative,
        "created_at": datetime.now(UTC).isoformat(),
        "project": project,
        "files": sorted([p.name for p in run_dir.iterdir() if p.is_file()]),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    # Update project metadata run counter
    increment_run_counter(project)
    # Prune if over limit
    if max_runs is not None:
        _prune_old_runs(proj_dir, max_runs)
    return run_dir

__all__ = ["persist_run", "get_base_output_dir"]
