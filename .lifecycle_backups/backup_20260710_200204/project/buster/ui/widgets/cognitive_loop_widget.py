from __future__ import annotations
from typing import Any, Dict
class CognitiveLoopWidgetModel:
    def __init__(self, data: Dict[str, Any] | None = None): self.data=data or {}
    def as_cards(self):
        return [{'label':'Mode','value':self.data.get('mode','unknown')},{'label':'Phase','value':self.data.get('phase','unknown')},{'label':'Ticks','value':self.data.get('tick_count',0)},{'label':'Last Thought','value':self.data.get('last_summary','')}]
