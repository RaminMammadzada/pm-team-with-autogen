from __future__ import annotations
"""Minimal FastAPI backend exposing project/run artifacts.

Endpoints:
- GET /projects -> list projects (name, slug, runs, created_at)
- GET /projects/{slug}/runs -> list run folders (ISO timestamp, path, initiative)
- GET /projects/{slug}/runs/{run_id}/artifact/{name} -> raw JSON/text artifact
- GET /projects/{slug}/runs/{run_id} -> manifest + selected artifacts summary
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pathlib import Path
import json
from .projects import list_projects, project_dir, create_project

app = FastAPI(title="PM Team API", version="0.1.0")

# CORS (allow local dev UI by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4300", "http://127.0.0.1:4300"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARTIFACT_FILES = ["plan.json", "release.json", "metrics.json", "aggregate_risk.txt", "stakeholder_summary.txt", "manifest.json"]


def _is_run_dir(p: Path) -> bool:
    return p.is_dir() and any((p / f).exists() for f in ("plan.json", "manifest.json"))


def _runs_for(slug: str):
    d = project_dir(slug)
    if not d.exists():
        return []
    return sorted([p for p in d.iterdir() if _is_run_dir(p)], key=lambda x: x.name, reverse=True)


class ProjectCreate(BaseModel):
    name: str = Field(..., description="Display name of the project")
    description: str | None = Field(None, description="Short description / purpose")
    domain: str | None = Field(None, description="Business or technical domain (e.g. claims, billing)")
    owner: str | None = Field(None, description="Primary responsible person/team")
    priority: str | None = Field(None, description="Relative priority or tier")
    tags: list[str] | None = Field(None, description="Free-form labels")


@app.get("/projects")
def get_projects():
    return list_projects()


@app.post("/projects", status_code=201)
def post_project(payload: ProjectCreate):
    try:
        meta = create_project(
            payload.name,
            description=payload.description,
            domain=payload.domain,
            owner=payload.owner,
            priority=payload.priority,
            tags=payload.tags,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return meta


@app.get("/projects/{slug}/runs")
def get_runs(slug: str):
    """List run folders for a project.

    Returns objects with keys:
      - run_id: canonical identifier (folder name) used by the frontend
      - id: alias for backward compatibility
      - initiative: optional initiative (from manifest.json)
      - created_at: optional timestamp if present in manifest (fallback None)
    """
    runs = []
    for r in _runs_for(slug):
        manifest = r / "manifest.json"
        initiative = None
        created_at = None
        if manifest.exists():
            try:
                mdata = json.loads(manifest.read_text())
                initiative = mdata.get("initiative")
                created_at = mdata.get("created_at") or mdata.get("timestamp") or mdata.get("started_at")
            except Exception:
                pass
        runs.append({
            "run_id": r.name,
            "id": r.name,  # legacy alias
            "initiative": initiative,
            "created_at": created_at,
        })
    return runs


@app.get("/projects/{slug}/runs/{run_id}")
def get_run_detail(slug: str, run_id: str):
    d = project_dir(slug) / run_id
    if not d.exists():
        raise HTTPException(404, "Run not found")
    data = {"id": run_id, "artifacts": {}}
    for f in ARTIFACT_FILES:
        p = d / f
        if p.exists():
            if p.suffix == ".json":
                try:
                    data["artifacts"][f] = json.loads(p.read_text())
                except Exception:
                    data["artifacts"][f] = None
            else:
                data["artifacts"][f] = p.read_text()[:2000]
    return data


@app.get("/projects/{slug}/runs/{run_id}/artifact/{name}")
def get_artifact(slug: str, run_id: str, name: str):
    d = project_dir(slug) / run_id / name
    if not d.exists():
        raise HTTPException(404, "Artifact not found")
    if d.suffix == ".json":
        try:
            return JSONResponse(json.loads(d.read_text()))
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=500)
    return PlainTextResponse(d.read_text())


# Simple health
@app.get("/health")
def health():
    return {"status": "ok"}
