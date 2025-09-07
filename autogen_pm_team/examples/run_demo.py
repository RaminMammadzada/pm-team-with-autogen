#!/usr/bin/env python3
from __future__ import annotations
import sys
import json
from pathlib import Path

# Make project root importable when run directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pm_team.orchestration import PMTeamOrchestrator  # noqa: E402
from pm_team.output_writer import persist_run  # noqa: E402


def main():
    initiative = (
        "Build an AI-powered analytics dashboard for customer churn insights"
        if len(sys.argv) < 2 else ' '.join(sys.argv[1:])
    )
    use_autogen = "--autogen" in sys.argv

    # Collect blockers (support multiple --blocker occurrences)
    blockers = []
    args_iter = enumerate(sys.argv)
    for i, token in args_iter:
        if token == "--blocker" and i + 1 < len(sys.argv):
            blockers.append(sys.argv[i + 1])

    single_blocker = blockers[0] if len(blockers) == 1 else None
    multi_blockers = blockers if len(blockers) > 1 else None

    wire_autogen_team = None
    if use_autogen:
        try:
            from pm_team.autogen_integration import wire_autogen_team  # type: ignore  # noqa: E402
        except ImportError as e:
            print(f"[ERROR] Autogen integration unavailable: {e}")
            use_autogen = False
    orchestrator = PMTeamOrchestrator()
    result = orchestrator.run(initiative, blocker=single_blocker, blockers=multi_blockers)

    # If autogen requested, perform conversational pass (planner -> release -> stakeholder)
    autogen_payload = None
    planner_msg = release_msg = stakeholder_msg = None  # predeclare for type safety
    if use_autogen and wire_autogen_team:
        team = wire_autogen_team()
        planner = team["planner"]
        release = team["release"]
        stakeholder = team["stakeholder"]
        # Planner
        planner_msg = planner.generate_reply(messages=[{"role": "user", "content": f"Initiative: {initiative}. Generate JSON plan."}])
        # Release
        release_msg = release.generate_reply(messages=[{"role": "user", "content": f"Sprint Plan JSON: {planner_msg}. Provide release JSON."}])
        # Stakeholder summary
        stakeholder_msg = stakeholder.generate_reply(messages=[{"role": "user", "content": f"Plan: {planner_msg}\nRelease: {release_msg}"}])
    autogen_payload = {
            "planner": planner_msg,
            "release": release_msg,
            "stakeholder": stakeholder_msg,
        }
    result["autogen_raw"] = autogen_payload

    print("=== Sprint Plan ===")
    print(f"Aggregate Risk Score: {result.get('aggregate_risk_score')}")
    for t in result['plan']['tasks']:
        print(f"{t['id']}: {t['title']} (pts={t['estimate_points']}, risk={t['risk']}, depends={t['depends_on']})")

    print("\n=== Release Summary ===")
    print(f"Window: {result['release']['window']}")
    print(f"Next Milestone: {result['release']['next_milestone']}")
    print("Notes:")
    for n in result['release']['notes']:
        print(f" - {n}")

    print("\n=== Stakeholder Summary ===")
    print(result['stakeholder_summary'])
    output_path = persist_run(result, autogen_payload, initiative)
    print(f"\nArtifacts saved to: {output_path}")

    if use_autogen and wire_autogen_team and autogen_payload:
        print("\n=== Autogen Outputs (Raw) ===")
        for k, v in autogen_payload.items():
            text = v if isinstance(v, str) else str(v)
            print(f"[{k}] {text[:400]}")


if __name__ == "__main__":
    main()
