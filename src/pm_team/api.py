from __future__ import annotations
"""Minimal FastAPI backend exposing project/run artifacts.

Endpoints:
- GET /projects -> list projects (name, slug, runs, created_at)
- GET /projects/{slug}/runs -> list run folders (ISO timestamp, path, initiative)
- GET /projects/{slug}/runs/{run_id}/artifact/{name} -> raw JSON/text artifact
- GET /projects/{slug}/runs/{run_id} -> manifest + selected artifacts summary
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pathlib import Path
import json
from .projects import list_projects, project_dir

app = FastAPI(title="PM Team API", version="0.1.0")

ARTIFACT_FILES = ["plan.json", "release.json", "metrics.json", "aggregate_risk.txt", "stakeholder_summary.txt", "manifest.json"]


def _is_run_dir(p: Path) -> bool:
    return p.is_dir() and any((p / f).exists() for f in ("plan.json", "manifest.json"))


def _runs_for(slug: str):
    d = project_dir(slug)
    if not d.exists():
        return []
    return sorted([p for p in d.iterdir() if _is_run_dir(p)], key=lambda x: x.name, reverse=True)


@app.get("/projects")
def get_projects():
    return list_projects()


@app.get("/projects/{slug}/runs")
def get_runs(slug: str):
    runs = []
    for r in _runs_for(slug):
        manifest = r / "manifest.json"
        initiative = None
        if manifest.exists():
            try:
                initiative = json.loads(manifest.read_text()).get("initiative")
            except Exception:
                pass
        runs.append({"id": r.name, "initiative": initiative})
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
