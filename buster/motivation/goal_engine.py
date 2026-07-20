# buster/motivation/goal_engine.py
import time
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class BusterGoal:
    id: str
    description: str
    category: str  # 'maintenance', 'optimization', 'learning'
    priority: int  # 1-5 Scale
    xp_reward: int
    completed: bool = False

class ProactiveGoalEngine:
    """Perceives codebases patterns and runtime anomalies to propose background maintenance goals."""
    
    def __init__(self):
        self.active_goals: List[BusterGoal] = []
        self.performance_score: int = 100
        self.last_environmental_check = 0.0

    def evaluate_environment(self, telemetry: Dict[str, Any]) -> List[BusterGoal]:
        """Ingests continuous status logs and compiles priority missions dynamically."""
        now = time.time()
        if now - self.last_environmental_check < 60.0:
            return self.active_goals  # Rate-limit parsing checks
            
        self.last_environmental_check = now
        new_goals = []

        # 1. Evaluate Test Outdated Gaps[cite: 9]
        days_since_test = telemetry.get("days_since_last_test_execution", 0)
        if days_since_test > 3:
            new_goals.append(BusterGoal(
                id="run_project_verification",
                description=f"Project verification run pending. Last checked {days_since_test} days ago.",
                category="maintenance",
                priority=3,
                xp_reward=150
            ))

        # 2. Evaluate Dead / Cluttered Imports[cite: 9]
        unused_imports = telemetry.get("unused_imports_count", 0)
        if unused_imports > 10:
            new_goals.append(BusterGoal(
                id="prune_dead_imports",
                description=f"Clean imports and fix optimization paths ({unused_imports} structural warnings found).",
                category="optimization",
                priority=2,
                xp_reward=200
            ))

        # 3. Evaluate Outdated Git Status
        git_commits_behind = telemetry.get("git_commits_behind", 0)
        if git_commits_behind > 5:
            new_goals.append(BusterGoal(
                id="sync_upstream_branch",
                description=f"Branch is {git_commits_behind} commits behind upstream. Run local reconciliation.",
                category="maintenance",
                priority=4,
                xp_reward=250
            ))

        # Merge new findings avoiding item duplication
        existing_ids = {g.id for g in self.active_goals if not g.completed}
        for g in new_goals:
            if g.id not in existing_ids:
                self.active_goals.append(g)

        return [g for g in self.active_goals if not g.completed]

    def trigger_goal_completion(self, goal_id: str) -> int:
        """Flags targeted goal items and emits reward point payouts to update state logs."""
        for goal in self.active_goals:
            if goal.id == goal_id and not goal.completed:
                goal.completed = True
                self.performance_score += int(goal.xp_reward * 0.2)
                return goal.xp_reward
        return 0

    def get_missions_context(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": g.id,
                "text": g.description,
                "priority": g.priority,
                "reward": f"+{g.xp_reward} XP"
            } for g in self.active_goals if not g.completed
        ]