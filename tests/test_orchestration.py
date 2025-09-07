from pm_team.orchestration import PMTeamOrchestrator


def test_basic_run(tmp_path):
    audit_file = tmp_path / "audit.jsonl"
    orch = PMTeamOrchestrator(audit_path=str(audit_file))
    result = orch.run("Test Initiative", blocker="Env setup delay")

    assert "plan" in result and "release" in result and "stakeholder_summary" in result
    assert len(result["plan"]["tasks"]) >= 6
    assert result["metrics"]["plans_created"] == 1
    assert result["metrics"]["blockers_recorded"] == 1

    content = audit_file.read_text().strip().splitlines()
    assert any("PLAN_CREATED" in line for line in content)
    assert any("BLOCKER_ADDED" in line for line in content)
    assert any("RUN_COMPLETED" in line for line in content)
