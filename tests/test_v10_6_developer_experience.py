import json

from buster.runtime import create_runtime_core


def main():
    core = create_runtime_core(".")
    core.start()

    core.run("Review architecture quality and validate with tests")

    payload = core.devtools.dashboard_payload()

    print("RUNTIME SUMMARY")
    print(json.dumps(payload["runtime"], indent=4, default=str))

    print()
    print("WORKFLOW GRAPH")
    print(json.dumps(payload["workflow_graph"], indent=4, default=str))

    print()
    print("EVENT GRAPH")
    print(json.dumps(payload["event_graph"]["summary"], indent=4, default=str))

    print()
    print("PLUGINS")
    print(json.dumps(payload["plugins"], indent=4, default=str))


if __name__ == "__main__":
    main()
