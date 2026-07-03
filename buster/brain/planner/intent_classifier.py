from buster.brain.types import Intent

class IntentClassifier:
    def classify(self, text: str) -> Intent:
        raw = text.strip()
        t = raw.lower()
        exact = {
            "performance": "performance", "perf": "performance", "services": "services", "service status": "services",
            "thread status": "threads", "threads": "threads", "tasks": "tasks", "task status": "task_status",
            "workspace": "workspace", "dashboard": "workspace", "index project": "repo_index", "repo status": "repo_status",
            "project status": "repo_status", "find todo": "repo_todos", "todos": "repo_todos", "largest files": "repo_largest",
            "ai status": "ai_status", "provider status": "ai_status", "use local": "ai_local", "use ollama": "ai_ollama",
            "use lm studio": "ai_lmstudio", "use openrouter": "ai_openrouter", "listen once": "voice_listen_once",
            "listen": "voice_listen_once", "start conversation": "voice_start", "stop conversation": "voice_stop",
            "voice status": "voice_status", "mic status": "voice_status", "start vision": "vision_start",
            "show vision": "vision_start", "open vision": "vision_start", "stop vision": "vision_stop",
            "vision status": "vision_status", "take photo": "vision_photo", "take picture": "vision_photo",
            "detect faces": "vision_faces", "detect objects": "vision_objects", "scan qr": "vision_qr",
            "scan barcode": "vision_qr", "read text": "vision_ocr", "learn my face": "vision_learn_face",
            "who am i": "vision_identify_face", "face status": "vision_face_status", "system status": "system_status",
            "agents": "agents", "plugins": "plugins", "hardware status": "hardware", "diagnostics": "diagnostics",
            "what do you remember": "memory_recall_all", "click": "click",
        }
        if t in exact:
            name = exact[t]
            if name == "ai_local": return Intent("ai_provider", "local", 0.98, raw)
            if name == "ai_ollama": return Intent("ai_provider", "ollama", 0.98, raw)
            if name == "ai_lmstudio": return Intent("ai_provider", "lmstudio", 0.98, raw)
            if name == "ai_openrouter": return Intent("ai_provider", "openrouter", 0.98, raw)
            if name == "vision_learn_face": return Intent(name, "Adam", 0.98, raw)
            return Intent(name, "", 0.98, raw)
        if t.startswith("remember "): return Intent("memory_remember", raw[len("remember "):].strip(), 0.98, raw)
        if t.startswith("what is my ") or t.startswith("what do i use") or t.startswith("what ide"): return Intent("memory_recall", raw, 0.95, raw)
        if t.startswith("learn face "): return Intent("vision_learn_face", raw[len("learn face "):].strip(), 0.98, raw)
        if t.startswith("find symbol "): return Intent("repo_find_symbol", raw[len("find symbol "):].strip(), 0.96, raw)
        if t.startswith("where is "): return Intent("repo_where", raw[len("where is "):].strip(), 0.96, raw)
        if t.startswith("index "): return Intent("repo_index", raw[len("index "):].strip() or ".", 0.96, raw)
        if t.startswith(("open ", "launch ", "start ")): return Intent("open", raw.split(" ", 1)[1], 0.95, raw)
        if t.startswith("search memory "): return Intent("memory_search", raw[len("search memory "):], 0.95, raw)
        if t.startswith("move mouse "): return Intent("move_mouse", raw[len("move mouse "):], 0.95, raw)
        if t.startswith("type "): return Intent("type_text", raw[len("type "):], 0.95, raw)
        for agent in ["builder", "tester", "fixer", "reviewer", "verifier"]:
            if t.startswith(agent + " "): return Intent("delegate", raw[len(agent)+1:], 0.93, raw)
        if t.startswith(("ask ", "question ")): return Intent("ai_answer", raw.split(" ", 1)[1], 0.90, raw)
        return Intent("ai_answer", raw, 0.55, raw)
