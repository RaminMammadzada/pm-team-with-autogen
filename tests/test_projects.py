from pm_team.projects import ensure_project, list_projects, increment_run_counter, project_dir
from pm_team.output_writer import persist_run


def test_project_creation_and_run(tmp_path, monkeypatch):
    # Redirect outputs root by changing CWD (simplest without refactor) – simulate isolated project root
    # NOTE: output_writer derives root via path traversal; we emulate by running inside tmp_path
    monkeypatch.chdir(tmp_path)
    p = ensure_project("Alpha Project")
    assert p["slug"] == "alpha_project"
    assert project_dir("Alpha Project").exists()
    assert len(list_projects()) == 1
    # Simulate run persistence
    result = {"plan": {"tasks": [], "blockers": [], "aggregate_risk_score": 0}, "release": {}, "stakeholder_summary": "", "metrics": {}}
    persist_run(result, None, "Test Initiative", project="Alpha Project")
    increment_run_counter("Alpha Project")
    updated = list_projects()[0]
    assert updated["runs"] >= 1
