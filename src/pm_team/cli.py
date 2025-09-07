from __future__ import annotations
import argparse
import sys
import os
from .orchestration import PMTeamOrchestrator
from .output_writer import persist_run
from .projects import (
    select_or_create_interactive,
    ensure_project,
    project_dir,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PM Team multi-agent demo")
    p.add_argument("initiative", help="Initiative description")
    p.add_argument("--blocker", action="append", default=[], help="Add a blocker (repeatable)")
    p.add_argument("--autogen", action="store_true", help="Use real Autogen agents if available")
    p.add_argument("--project", help="Project name to use (existing or new if --create-project)")
    p.add_argument("--create-project", help="Force creation of a new project with given name")
    p.add_argument("--list-projects", action="store_true", help="List existing projects and exit")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout (plan+release+summary)")
    p.add_argument("--max-runs", type=int, default=None, help="If set, prune oldest run dirs beyond this count for the project")
    return p


def main(argv=None):  # pragma: no cover - thin wrapper
    parser = build_parser()
    args = parser.parse_args(argv)
    # Early listing mode
    if args.list_projects:
        from .projects import list_projects
        projects = list_projects()
        if not projects:
            print("<no projects>")
            return 0
        print("Projects:")
        for p in projects:
            print(f" - {p['name']} (slug={p['slug']}, runs={p.get('runs', 0)})")
        return 0
    # Determine project name (interactive if not provided)
    project_name = None
    if args.create_project:
        project_name = args.create_project
        ensure_project(project_name)
    elif args.project:
        project_name = args.project
        # auto-create if not existing
        ensure_project(project_name)
    else:
        project_name = select_or_create_interactive()

    proj_audit = project_dir(project_name) / "audit_log.jsonl"
    orchestrator = PMTeamOrchestrator(audit_path=str(proj_audit))
    single_blocker = args.blocker[0] if len(args.blocker) == 1 else None
    multi_blockers = args.blocker if len(args.blocker) > 1 else None
    result = orchestrator.run(args.initiative, blocker=single_blocker, blockers=multi_blockers)

    autogen_payload = None
    if args.autogen:
        try:
            from .autogen_integration import wire_autogen_team  # type: ignore
            team = wire_autogen_team()
            planner_msg = team["planner"].generate_reply(messages=[{"role": "user", "content": f"Initiative: {args.initiative}. Generate JSON plan."}])
            release_msg = team["release"].generate_reply(messages=[{"role": "user", "content": f"Sprint Plan JSON: {planner_msg}. Provide release JSON."}])
            stakeholder_msg = team["stakeholder"].generate_reply(messages=[{"role": "user", "content": f"Plan: {planner_msg}\nRelease: {release_msg}"}])
            autogen_payload = {"planner": planner_msg, "release": release_msg, "stakeholder": stakeholder_msg}
            result["autogen_raw"] = autogen_payload
        except ImportError as e:
            print(f"[WARN] Autogen unavailable: {e}")

    import json as _json
    output_path = persist_run(result, autogen_payload, args.initiative, project=project_name, max_runs=args.max_runs)
    if args.json:
        payload = {
            "initiative": args.initiative,
            "project": project_name,
            "plan": result["plan"],
            "release": result["release"],
            "stakeholder_summary": result["stakeholder_summary"],
            "metrics": result["metrics"],
            "aggregate_risk_score": result.get("aggregate_risk_score"),
            "artifacts_path": str(output_path),
        }
        print(_json.dumps(payload, ensure_ascii=False))
    else:
        print("=== Sprint Plan ===")
        print(f"Aggregate Risk Score: {result.get('aggregate_risk_score')}")
        for t in result["plan"]["tasks"]:
            print(f"{t['id']}: {t['title']} (pts={t['estimate_points']}, risk={t['risk']}, depends={t['depends_on']})")

        print("\n=== Release Summary ===")
        print(f"Window: {result['release']['window']}")
        print(f"Next Milestone: {result['release']['next_milestone']}")
        print("Notes:")
        for n in result["release"]["notes"]:
            print(f" - {n}")

        print("\n=== Stakeholder Summary ===")
        print(result["stakeholder_summary"])
        print(f"\nArtifacts saved to: {output_path}")

        if autogen_payload:
            print("\n=== Autogen Outputs (Raw) ===")
            for k, v in autogen_payload.items():
                text = v if isinstance(v, str) else str(v)
                print(f"[{k}] {text[:400]}")


if __name__ == "__main__":  # pragma: no cover
    main()
