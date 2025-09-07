from __future__ import annotations
import argparse
from .orchestration import PMTeamOrchestrator
from .output_writer import persist_run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PM Team multi-agent demo")
    p.add_argument("initiative", help="Initiative description")
    p.add_argument("--blocker", action="append", default=[], help="Add a blocker (repeatable)")
    p.add_argument("--autogen", action="store_true", help="Use real Autogen agents if available")
    return p


def main(argv=None):  # pragma: no cover - thin wrapper
    parser = build_parser()
    args = parser.parse_args(argv)
    orchestrator = PMTeamOrchestrator()
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
    output_path = persist_run(result, autogen_payload, args.initiative)
    print(f"\nArtifacts saved to: {output_path}")

    if autogen_payload:
        print("\n=== Autogen Outputs (Raw) ===")
        for k, v in autogen_payload.items():
            text = v if isinstance(v, str) else str(v)
            print(f"[{k}] {text[:400]}")


if __name__ == "__main__":  # pragma: no cover
    main()
