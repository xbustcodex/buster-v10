from __future__ import annotations

import argparse
import json
from .doctor import BusterDoctor
from .repair import BusterRepair


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="buster-builder", description="Buster self-maintenance tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check project health")
    sub.add_parser("repair", help="Apply safe repairs")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        result = BusterDoctor().run()
    elif args.command == "repair":
        result = BusterRepair().run()
    else:
        parser.error("unknown command")
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
