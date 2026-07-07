import json

from buster.runtime import create_runtime_core


def main():
    core = create_runtime_core(".")

    print("START")
    print(json.dumps(core.start(), indent=4, default=str))

    print()
    print("CORE STATUS")
    print(json.dumps({
        "started": core.status()["started"],
        "registry_summary": core.status()["registry_summary"],
        "services": core.sdk.registry.names(),
        "agents": core.agents.names(),
    }, indent=4, default=str))

    print()
    print("RUN ORCHESTRATED REQUEST")
    result = core.run("Review architecture quality and validate with tests")
    print(json.dumps({
        "status": result["status"],
        "selected_agents": result["selected_agents"],
        "jobs": len(result["jobs"]),
    }, indent=4, default=str))

    print()
    print("BLACKBOARD GOAL")
    print(json.dumps(core.blackboard.read("goal"), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(core.events.recent(20), indent=4, default=str))


if __name__ == "__main__":
    main()
