from pm_team.cli import main as cli_main
from pm_team.projects import ensure_project, list_projects, project_dir
from pm_team.output_writer import persist_run
from pm_team.orchestration import PMTeamOrchestrator


def test_project_creation_and_run_isolation(tmp_path, monkeypatch):
    # Use temp outputs root
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outputs"))
    ensure_project("Alpha One")
    ensure_project("Beta Two")
    projects = list_projects()
    names = {p["name"] for p in projects}
    assert {"Alpha One", "Beta Two"}.issubset(names)

    orch = PMTeamOrchestrator(audit_path=str((project_dir("Alpha One") / "audit_log.jsonl")))
    res = orch.run("Alpha Feature", blocker="latency")
    assert res["plan"]["tasks"], "Plan tasks should exist"

    # Persist run under Alpha project
    run_path = persist_run(res, None, "Alpha Feature", project="Alpha One")
    assert run_path.parent.name == project_dir("Alpha One").name
    assert (run_path / "plan.json").exists()

    # Beta should have no runs yet
    beta_dir = project_dir("Beta Two")
    beta_runs = [d for d in beta_dir.iterdir() if d.is_dir() and d.name != "audit_log.jsonl"]
    assert beta_runs == [], "Beta project should not yet have run directories"


def test_cli_list_projects(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PM_TEAM_OUTPUT_ROOT", str(tmp_path / "outs"))
    ensure_project("Gamma")
    ensure_project("Delta")
    # Invoke list (initiative positional still required)
    cli_main(["Placeholder initiative", "--list-projects"])  # initiative ignored for listing
    out = capsys.readouterr().out
    assert "Gamma" in out and "Delta" in out
