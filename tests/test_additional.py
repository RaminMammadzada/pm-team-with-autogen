import json
import os
from pathlib import Path

from pm_team.orchestration import PMTeamOrchestrator
from pm_team.output_writer import persist_run
from pm_team.projects import select_or_create_interactive, ensure_project, project_dir, _slug as _project_slug  # type: ignore
from pm_team.cli import main as cli_main


def test_multi_blockers_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outs"))
    audit = tmp_path / "audit.jsonl"
    orch = PMTeamOrchestrator(audit_path=str(audit))
    res = orch.run("Latency Optimization", blocker="network", blockers=["db", "cache"])
    # 6 base tasks + 3 mitigation tasks = 9 tasks
    assert len(res["plan"]["tasks"]) == 9
    # blockers_recorded should be 3
    assert res["metrics"]["blockers_recorded"] == 3
    # Audit file should contain three BLOCKER_ADDED lines
    lines = audit.read_text().strip().splitlines()
    blocker_events = [l for l in lines if 'BLOCKER_ADDED' in l]
    assert len(blocker_events) == 3


def test_persist_run_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outs"))
    ensure_project("ArtifactsProj")
    orch = PMTeamOrchestrator(audit_path=str(project_dir("ArtifactsProj") / "audit_log.jsonl"))
    res = orch.run("Feature Delivery", blocker="integration")
    fake_autogen = {"planner": "plan raw", "release": "release raw", "stakeholder": "summary raw"}
    run_dir = persist_run(res, fake_autogen, "Feature Delivery", project="ArtifactsProj")
    expected_files = {"plan.json", "release.json", "metrics.json", "aggregate_risk.txt", "stakeholder_summary.txt", "manifest.json"}
    present_files = {p.name for p in run_dir.iterdir() if p.is_file()}
    assert expected_files.issubset(present_files)
    auto_dir = run_dir / "autogen"
    assert auto_dir.exists() and any(auto_dir.iterdir())
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["initiative"] == "Feature Delivery" and manifest["project"] == "ArtifactsProj"


def test_noninteractive_default_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outs"))
    monkeypatch.setenv("PM_TEAM_NONINTERACTIVE", "1")
    # Should auto-create default
    name = select_or_create_interactive()
    assert name == "default"
    d = project_dir("default")
    assert d.exists() and (d / "project.json").exists()
    data = json.loads((d / "project.json").read_text())
    assert data["slug"] == _project_slug("default")


def test_cli_json_and_prune(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outs"))
    ensure_project("PruneProj")
    # Create 3 runs with --json and pruning to keep only 2
    for i in range(3):
        cli_main([f"Initiative {i}", "--project", "PruneProj", "--json", "--max-runs", "2"])
    proj = project_dir("PruneProj")
    run_dirs = [d for d in proj.iterdir() if d.is_dir()]
    assert len(run_dirs) == 2, f"Should retain only 2 runs, got {len(run_dirs)}"
    # Validate JSON printed
    out = capsys.readouterr().out.strip().splitlines()
    assert out, "Expected JSON output lines"
    import json as _json
    parsed = _json.loads(out[-1])
    assert parsed["project"] == "PruneProj" and "plan" in parsed
