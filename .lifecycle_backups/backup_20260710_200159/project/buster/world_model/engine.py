from datetime import datetime, timezone
from .storage import WorldModelStorage
from .entities import WorldEntity
from .observations import Observation
from .relationships import Relationship
from .memory import WorldMemory
from .understanding import UnderstandingEngine

class WorldModelEngine:
    def __init__(self, data_dir="data"):
        self.storage = WorldModelStorage(data_dir)
        self.state = self.storage.load()
        self.memory = WorldMemory()
        self.understanding = UnderstandingEngine()

    def add_entity(self, kind, name, attributes=None, confidence=0.75):
        entity = WorldEntity(kind=kind, name=name, attributes=attributes or {}, confidence=confidence)
        self.state.setdefault("entities", []).append(entity.to_dict())
        self._timeline("entity_added", f"{kind}: {name}", confidence)
        self.storage.save(self.state)
        return entity.to_dict()

    def observe(self, source, summary, context=None, importance=0.5, confidence=0.75):
        obs = Observation(source=source, summary=summary, context=context or {}, importance=importance, confidence=confidence)
        data = obs.to_dict()
        self.state.setdefault("observations", []).append(data)
        self.memory.remember_short_term(data)
        if importance >= 0.7:
            self.memory.remember_episode(data)
        self._timeline("observation", summary, confidence)
        self.storage.save(self.state)
        return data

    def link(self, source_id, target_id, relation, confidence=0.75):
        rel = Relationship(source_id=source_id, target_id=target_id, relation=relation, confidence=confidence)
        self.state.setdefault("relationships", []).append(rel.to_dict())
        self._timeline("relationship", relation, confidence)
        self.storage.save(self.state)
        return rel.to_dict()

    def understand_now(self):
        recent = self.state.get("observations", [])[-20:]
        context = self.understanding.infer_context(recent)
        recommendation = self.understanding.recommend(context)
        snapshot = {
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "context": context,
            "recommendation": recommendation,
            "entity_count": len(self.state.get("entities", [])),
            "observation_count": len(self.state.get("observations", [])),
            "relationship_count": len(self.state.get("relationships", [])),
        }
        self.state["current_understanding"] = snapshot
        self.storage.save(self.state)
        return snapshot

    def _timeline(self, event_type, summary, confidence):
        self.state.setdefault("timeline", []).append({
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": event_type,
            "summary": summary,
            "confidence": confidence,
        })
        self.state["timeline"] = self.state["timeline"][-500:]

    def dashboard(self):
        understanding = self.state.get("current_understanding") or self.understand_now()
        return {
            "title": "World Model",
            "status": "online",
            "understanding": understanding,
            "recent_timeline": self.state.get("timeline", [])[-10:],
            "memory": self.memory.snapshot(),
        }
