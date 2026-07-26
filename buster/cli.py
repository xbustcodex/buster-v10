# buster/cli.py
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from buster.capabilities.registry import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.agent.core import BusterAgent
from buster.agent.llm_planner import LLMIntentPlanner


def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))
    return registry


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Buster Autonomous AI Agent CLI")
    parser.add_argument("goal", nargs="?", help="Natural language goal for Buster to execute")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive REPL mode")

    args = parser.parse_args(argv)

    registry = create_registry()
    agent = BusterAgent(registry)
    planner = LLMIntentPlanner(agent)

    if args.interactive:
        print("=== Buster Interactive REPL ===")
        print("Type your goals below (or 'exit' / 'quit' to leave).")
        while True:
            try:
                user_input = input("\nbuster> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break
                
                print(f"Executing goal: '{user_input}'...")
                ctx = planner.run_natural_language_goal(user_input)
                print(f"Mission Status: SUCCESS. Outputs: {ctx.outputs}")
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Mission Error: {e}")
        return 0

    if args.goal:
        try:
            print(f"Executing goal: '{args.goal}'...")
            ctx = planner.run_natural_language_goal(args.goal)
            print(f"Mission Success! Outputs: {ctx.outputs}")
            return 0
        except Exception as e:
            print(f"Mission Failed: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())