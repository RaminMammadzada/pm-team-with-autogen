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
from .output_writer import persist_run
from .conversation import load_conversation, agent_reply
from .plan_ops import add_blocker_task, reprioritize_tasks
from .plan_diff import diff_plans
from .orchestration import PMTeamOrchestrator

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


class RunCreate(BaseModel):
    initiative: str = Field(..., description="Initiative description to generate a plan for")
    blocker: str | None = Field(None, description="Optional single blocker")
    blockers: list[str] | None = Field(None, description="Optional list of blockers if more than one")
    max_runs: int | None = Field(None, description="Optional retention for run directories")


@app.post("/projects/{slug}/runs", status_code=201)
def create_run(slug: str, payload: RunCreate):
    # Ensure project exists
    from .projects import ensure_project
    ensure_project(slug)
    orchestrator = PMTeamOrchestrator(audit_path=str(project_dir(slug) / "audit_log.jsonl"))
    single_blocker = payload.blocker if payload.blocker and not payload.blockers else None
    multi_blockers = payload.blockers if payload.blockers else ( [payload.blocker] if (payload.blocker and not payload.blockers) else None )
    result = orchestrator.run(payload.initiative, blocker=single_blocker, blockers=multi_blockers)
    run_dir = persist_run(result, None, payload.initiative, project=slug, max_runs=payload.max_runs)
    run_id = run_dir.name
    return {"run_id": run_id, "initiative": payload.initiative}


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


@app.get("/projects/{slug}/plan-diff")
def get_plan_diff(slug: str, old_run: str, new_run: str):
    """Compute diff between plan.json of two runs.

    Query params: old_run, new_run
    """
    old_dir = project_dir(slug) / old_run
    new_dir = project_dir(slug) / new_run
    if not old_dir.exists() or not new_dir.exists():
        raise HTTPException(404, "One or both runs not found")
    old_plan = None
    new_plan = None
    try:
        op = old_dir / "plan.json"
        if op.exists():
            old_plan = json.loads(op.read_text())
    except Exception:
        old_plan = None
    try:
        np = new_dir / "plan.json"
        if np.exists():
            new_plan = json.loads(np.read_text())
    except Exception:
        new_plan = None
    return diff_plans(old_plan, new_plan)


@app.get("/projects/{slug}/runs/{run_id}/chat")
def get_chat(slug: str, run_id: str):
    d = project_dir(slug) / run_id
    if not d.exists():
        raise HTTPException(404, "Run not found")
    messages = load_conversation(d)
    return {"messages": messages}


class ChatPost(BaseModel):
    message: str = Field(..., description="User prompt / query")
    mode: str | None = Field(None, description="Optional action mode: status|risk|add_blocker|reprioritize")
    blocker: str | None = Field(None, description="Blocker description when mode=add_blocker")
    order: list[str] | None = Field(None, description="Task ID ordering when mode=reprioritize (partial allowed)")


@app.post("/projects/{slug}/runs/{run_id}/chat")
def post_chat(slug: str, run_id: str, payload: ChatPost):
    content = (payload.message or "").strip()
    if not content and not payload.mode:
        raise HTTPException(400, "Empty message")
    d = project_dir(slug) / run_id
    if not d.exists():
        raise HTTPException(404, "Run not found")

    # Pre-action mutations (deterministic) before LLM response
    system_notes: list[str] = []
    if payload.mode == "add_blocker":
        if not payload.blocker:
            raise HTTPException(400, "blocker field required for mode=add_blocker")
        try:
            add_blocker_task(d, payload.blocker)
            system_notes.append(f"Added blocker and mitigation task: {payload.blocker}")
        except FileNotFoundError:
            raise HTTPException(409, "Plan not found for this run")
    elif payload.mode == "reprioritize":
        if not payload.order:
            raise HTTPException(400, "order list required for mode=reprioritize")
        try:
            reprioritize_tasks(d, payload.order)
            system_notes.append(f"Reprioritized tasks (partial order applied): {', '.join(payload.order)}")
        except FileNotFoundError:
            raise HTTPException(409, "Plan not found for this run")

    # Augment user content with system notes (so agent can explain change)
    augmented = content
    if system_notes:
        augmented = (content + "\n\n" if content else "") + "SYSTEM_UPDATES:\n" + "\n".join(system_notes)
    reply, history = agent_reply(d, slug, augmented or content)
    return {"reply": reply, "messages": history, "system_updates": system_notes}


# Simple health
@app.get("/health")
def health():
    return {"status": "ok"}
