import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    orchestrator = system["orchestrator"]
    registry = system["registry"]
    blackboard = system["blackboard"]
    memory = system["agent_memory"]
    sdk = system["sdk"]

    runtime.start()

    result = orchestrator.run(
        "Build a safe runtime feature, validate it, review architecture quality"
    )

    print("REGISTRY")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("ORCHESTRATION RESULT")
    print(json.dumps({
        "status": result["status"],
        "selected_agents": result["selected_agents"],
        "jobs": len(result["jobs"]),
    }, indent=4, default=str))

    print()
    print("BLACKBOARD")
    print(json.dumps(blackboard.snapshot(), indent=4, default=str))

    print()
    print("AGENT MEMORY")
    print(json.dumps(memory.status(), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(30), indent=4, default=str))


if __name__ == "__main__":
    main()
