from buster.brain.types import Plan
from buster.brain.planner.intent_classifier import IntentClassifier

class AIPlanner:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.last_plan = None

    def make_plan(self, text: str) -> Plan:
        intent = self.classifier.classify(text)
        mapping = {
            "performance": "performance.status", "services": "services.status", "threads": "threads.status",
            "tasks": "tasks.list", "task_status": "tasks.status", "workspace": "workspace.status",
            "repo_index": "repo.index", "repo_status": "repo.status", "repo_find_symbol": "repo.find_symbol",
            "repo_where": "repo.where", "repo_todos": "repo.todos", "repo_largest": "repo.largest",
            "memory_remember": "knowledge.remember", "memory_recall": "knowledge.recall", "memory_recall_all": "knowledge.recall_all",
            "ai_status": "ai.status", "ai_provider": "ai.provider", "ai_answer": "ai.answer",
            "open": "apps.open", "memory_search": "memory.search", "system_status": "system.status", "agents": "agents.status",
            "move_mouse": "automation.move_mouse", "type_text": "automation.type_text", "click": "automation.click",
            "voice_status": "voice.status", "voice_start": "voice.start", "voice_stop": "voice.stop", "voice_listen_once": "voice.listen_once",
            "vision_status": "vision.status", "vision_start": "vision.start", "vision_stop": "vision.stop", "vision_photo": "vision.photo",
            "vision_faces": "vision.faces", "vision_objects": "vision.objects", "vision_qr": "vision.qr", "vision_ocr": "vision.ocr",
            "vision_learn_face": "vision.learn_face", "vision_identify_face": "vision.identify_face", "vision_face_status": "vision.face_status",
            "plugins": "plugins.status", "hardware": "hardware.status", "diagnostics": "diagnostics.report", "delegate": "agents.delegate",
        }
        agent = intent.raw.split(" ", 1)[0].lower() if intent.name == "delegate" else ""
        plan = Plan(intent=intent, action=mapping.get(intent.name, "ai.answer"), target=intent.target, agent=agent)
        self.last_plan = plan
        return plan

    def describe(self):
        if not self.last_plan: return "No plan yet."
        p = self.last_plan
        return f"Intent: {p.intent.name}\nConfidence: {int(p.intent.confidence * 100)}%\nAction: {p.action}\nTarget: {p.target or 'none'}\nAgent: {p.agent or 'none'}\nStatus: {p.status}"
