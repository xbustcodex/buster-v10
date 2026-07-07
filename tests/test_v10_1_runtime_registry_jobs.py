import json

from buster.runtime.sdk_bootstrap import build_sdk_runtime


def main():
    system = build_sdk_runtime(".")
    runtime = system["runtime"]
    sdk = system["sdk"]
    agents = system["agents"]
    registry = system["registry"]
    jobs = system["jobs"]

    runtime.start()

    print("REGISTRY STATUS")
    print(json.dumps(registry.status()["summary"], indent=4, default=str))

    print()
    print("CAPABILITY: health")
    print(json.dumps(
        agents.run("registry", {"action": "capability", "capability": "health"}),
        indent=4,
        default=str,
    ))

    print()
    print("CREATE JOB")
    job = agents.run("jobs", {
        "action": "create",
        "title": "Run lifecycle health check",
        "job_type": "lifecycle.health",
        "payload": {"requested_by": "v10.1_test"},
    })
    print(json.dumps(job, indent=4, default=str))

    print()
    print("RUN JOB")
    completed = agents.run("jobs", {
        "action": "run",
        "job_id": job["job_id"],
    })
    print(json.dumps(completed, indent=4, default=str))

    print()
    print("JOB MANAGER STATUS")
    print(json.dumps(jobs.status(), indent=4, default=str))

    print()
    print("REGISTRY JOBS")
    print(json.dumps(registry.status()["jobs"], indent=4, default=str))

    print()
    print("RECENT EVENTS")
    print(json.dumps(sdk.events.recent(25), indent=4, default=str))


if __name__ == "__main__":
    main()
