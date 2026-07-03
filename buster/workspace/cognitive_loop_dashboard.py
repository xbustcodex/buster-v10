from __future__ import annotations
from typing import Any, Dict
from buster.mind.cognitive_loop import CognitiveLoopEngine
from buster.mind.internal_dialogue import InternalDialogue
from buster.mind.dream_mode import DreamMode
class CognitiveLoopDashboard:
    def snapshot(self) -> Dict[str, Any]:
        state=CognitiveLoopEngine().status(); dialogue=InternalDialogue(); dream=DreamMode()
        return {'title':'Cognitive Loop','enabled':state.get('enabled',False),'mode':state.get('mode','unknown'),'phase':state.get('current_phase','unknown'),'tick_count':state.get('tick_count',0),'last_summary':state.get('last_summary',''),'recent_steps':state.get('recent_steps',[])[-10:],'internal_dialogue':dialogue.recent(10),'dream_reflections':dream.recent(5)}
