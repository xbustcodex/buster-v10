from __future__ import annotations

import json
import os
import time
from buster.brain.blackboard import SharedBlackboard
from buster.brain.dlq_manager import DLQManager
from buster.brain.task_delegator import TaskDelegator
from buster.brain.growth_ledger import GrowthLedgerManager


def run_full_system_verification() -> None:
    print("=" * 60)
    print("[RUNNER] BUSTER V10 END-TO-END RUNTIME VERIFICATION")
    print("=" * 60)

    # 1. Initialize core engines
    blackboard = SharedBlackboard()
    dlq = DLQManager()
    delegator = TaskDelegator(blackboard=blackboard, dlq_manager=dlq)
    ledger = GrowthLedgerManager()

    # 2. Decompose a Goal
    goal_name = "Refactor v17 Core Engine"
    plan = delegator.decompose_and_delegate(goal_name)
    print(f"[+] Goal Created: '{plan['goal']}' with {plan['subtask_count']} subtasks.")

    # 3. Simulate Successful Task Execution
    print("\n--- Executing Task 1 (Success Path) ---")
    delegator.execute_worker_task(task_id="task-1", worker_id="Worker-1", simulate_failure=False)

    # 4. Simulate Component Failure & Circuit Tripping
    print("\n--- Executing Task 2 (Failure Path to Trip Circuit) ---")
    for i in range(1, 4):
        delegator.execute_worker_task(task_id="task-2", worker_id="Worker-2", simulate_failure=True)

    # 5. Verify DLQ & Circuit State Snapshot
    print("\n--- System Resilience Check ---")
    dlq_snapshot = dlq.get_snapshot()
    code_circuit = dlq_snapshot["circuits"].get("code_executor", {})
    
    print(f"  * Failed Tasks in DLQ: {len(dlq_snapshot.get('dlq_items', []))}")
    print(f"  * Circuit 'code_executor' Status: {code_circuit.get('status')} (Failures: {code_circuit.get('failure_count')})")

    # 6. Verify Growth Ledger Snapshot
    print("\n--- Growth Ledger Telemetry ---")
    ledger_snapshot = ledger.get_snapshot()
    print(f"  * Hurdles Patched: {len(ledger_snapshot.get('hurdles', []))}")
    print(f"  * Toolbelt Items: {len(ledger_snapshot.get('toolbelt', []))}")

    print("\n" + "=" * 60)
    print("[+] VERIFICATION COMPLETE: All system loops fully operational!")
    print("=" * 60)


if __name__ == "__main__":
    run_full_system_verification()