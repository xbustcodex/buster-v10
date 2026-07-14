from __future__ import annotations
from typing import Any, Dict
def cognitive_loop_context_for_planner(loop_state: Dict[str, Any]) -> Dict[str, Any]:
    phase=loop_state.get('current_phase','idle')
    return {'cognitive_phase':phase,'loop_enabled':loop_state.get('enabled',True),'mode':loop_state.get('mode','companion'),'last_summary':loop_state.get('last_summary',''),'should_plan':phase in {'plan','review_goals','act'},'should_reflect':phase in {'learn','reflect'}}
