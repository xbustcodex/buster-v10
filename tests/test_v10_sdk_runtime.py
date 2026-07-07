import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    sdk = system["sdk"]
    agents = system["agents"]

    print("START")
    print(json.dumps(runtime.start(), indent=4, default=str))

    print()
    print("SDK STATUS")
    print(json.dumps(sdk.status(), indent=4, default=str))

    print()
    print("SERVICES")
    print(json.dumps(sdk.registry.names(), indent=4, default=str))

    print()
    print("AGENTS")
    print(json.dumps(agents.names(), indent=4, default=str))

    print()
    print("LIFECYCLE STATUS")
    print(json.dumps(agents.run("lifecycle", "status"), indent=4, default=str))

    print()
    print("LIFECYCLE HEALTH")
    print(json.dumps(agents.run("lifecycle", "health"), indent=4, default=str))

    print()
    print("TICK")
    print(json.dumps(runtime.tick_once([{
        "type": "workspace",
        "summary": "python development in buster v10 runtime",
    }]), indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(20), indent=4, default=str))


if __name__ == "__main__":
    main()
