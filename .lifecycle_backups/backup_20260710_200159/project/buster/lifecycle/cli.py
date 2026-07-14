import argparse
import json

from .manager import LifecycleManager


def main():
    parser = argparse.ArgumentParser(description="Buster Lifecycle Manager")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("--root", default=".")
    parser.add_argument("--yes", action="store_true")

    args = parser.parse_args()

    manager = LifecycleManager(args.root)

    if args.command == "status":
        print(json.dumps(manager.status(), indent=4))

    elif args.command == "scan":
        print(json.dumps(manager.scanner.scan(), indent=4))

    elif args.command == "plan":
        print(json.dumps(manager.plan(), indent=4))

    elif args.command == "backup":
        print(manager.backup())

    elif args.command == "verify":
        print(json.dumps(manager.verify(), indent=4))

    elif args.command == "upgrade":
        ok = manager.apply_manifest(auto_confirm=args.yes)
        print("Upgrade completed." if ok else "Upgrade failed.")

    elif args.command == "rollback":
        ok = manager.rollback()
        print("Rollback completed." if ok else "Rollback failed.")

    elif args.command == "health":
        print(json.dumps(manager.run_health(), indent=4))

    else:
        print("Commands: status, scan, plan, backup, verify, upgrade, rollback, health")


if __name__ == "__main__":
    main()
