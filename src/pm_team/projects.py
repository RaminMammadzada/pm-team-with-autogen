from __future__ import annotations
"""Multi-project management utilities.

Each project has its own directory under the root `outputs/` folder:

outputs/
  <project_slug>/
     project.json        # metadata { name, slug, created_at, runs }
     audit_log.jsonl     # per-project audit trail
     <run folders>...

This module centralizes project creation, listing, and metadata updates.
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
import json
import re
import os

SANITIZE_RE = re.compile(r"[^a-z0-9_\-]+")


def _slug(name: str) -> str:
    s = name.strip().lower().replace(" ", "_")
    return SANITIZE_RE.sub("", s) or "default"


def outputs_root() -> Path:
    # Reuse logic from output_writer indirectly: root project dir is parent of src
    return Path(__file__).resolve().parents[2] / "outputs"


def project_dir(name: str) -> Path:
    return outputs_root() / _slug(name)


def project_meta_path(name: str) -> Path:
    return project_dir(name) / "project.json"


def list_projects() -> List[Dict]:
    root = outputs_root()
    if not root.exists():
        return []
    projects: List[Dict] = []
    for d in root.iterdir():
        if d.is_dir():
            meta = d / "project.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text())
                    projects.append(data)
                except Exception:
                    pass
    # Sort by created_at ascending
    return sorted(projects, key=lambda x: x.get("created_at", ""))


def ensure_project(name: str) -> Dict:
    """Ensure a minimal project exists (legacy helper)."""
    d = project_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    meta_p = d / "project.json"
    if meta_p.exists():
        try:
            return json.loads(meta_p.read_text())
        except Exception:
            pass
    meta = {"name": name, "slug": _slug(name), "created_at": datetime.now(UTC).isoformat(), "runs": 0}
    meta_p.write_text(json.dumps(meta, indent=2))
    return meta


def create_project(name: str, **kwargs: Any) -> Dict:
    """Create a project with extended metadata.

    Existing project slug raises ValueError.
    Extra keyword fields are merged into the metadata file.
    """
    d = project_dir(name)
    if d.exists() and (d / "project.json").exists():
        raise ValueError("project already exists")
    d.mkdir(parents=True, exist_ok=True)
    meta: Dict[str, Any] = {
        "name": name,
        "slug": _slug(name),
        "created_at": datetime.now(UTC).isoformat(),
        "runs": 0,
    }
    # Only include provided non-null extras
    for k, v in kwargs.items():
        if v is not None:
            meta[k] = v
    (d / "project.json").write_text(json.dumps(meta, indent=2))
    return meta


def increment_run_counter(name: str):
    meta_p = project_meta_path(name)
    if not meta_p.exists():
        ensure_project(name)
        return
    try:
        data = json.loads(meta_p.read_text())
    except Exception:
        data = {"name": name, "slug": _slug(name), "created_at": datetime.now(UTC).isoformat(), "runs": 0}
    data["runs"] = int(data.get("runs", 0)) + 1
    meta_p.write_text(json.dumps(data, indent=2))


def select_or_create_interactive() -> str:
    """Prompt user to select existing project or create a new one.

    Falls back to 'default' in non-interactive environments.
    """
    if os.getenv("PM_TEAM_NONINTERACTIVE") == "1":
        ensure_project("default")
        return "default"
    projects = list_projects()
    if not projects:
        # No existing projects; create default or ask for name
        try:
            raw = input("No projects found. Enter new project name (blank for 'default'): ").strip()
        except Exception:
            raw = "default"
        name = raw or "default"
        ensure_project(name)
        return name
    print("Select a project or create a new one:")
    for idx, p in enumerate(projects, start=1):
        print(f"  {idx}) {p['name']} (runs={p.get('runs', 0)})")
    print("  n) New project")
    try:
        choice = input("Choice: ").strip().lower()
    except Exception:
        return projects[0]["name"]
    if choice == "n":
        try:
            new_name = input("New project name: ").strip()
        except Exception:
            new_name = "default"
        if not new_name:
            new_name = "default"
        ensure_project(new_name)
        return new_name
    try:
        idx = int(choice)
        if 1 <= idx <= len(projects):
            return projects[idx - 1]["name"]
    except ValueError:
        pass
    # Fallback first project
    return projects[0]["name"]


__all__ = [
    "list_projects",
    "ensure_project",
    "create_project",
    "increment_run_counter",
    "select_or_create_interactive",
    "project_dir",
]
