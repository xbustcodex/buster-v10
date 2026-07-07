import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    workflow = system["workflow"]
    registry = system["registry"]
    sdk = system["sdk"]

    runtime.start()

    print("REGISTRY SUMMARY")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("RUN WORKFLOW")
    result = workflow.run_request("Build a safe runtime feature and validate it with tests")
    print(json.dumps(result, indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(30), indent=4, default=str))


if __name__ == "__main__":
    main()
