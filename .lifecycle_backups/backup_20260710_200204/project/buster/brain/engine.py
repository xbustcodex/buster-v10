from buster.brain.planner.planner import AIPlanner
from buster.intelligence.project_intelligence import ProjectIntelligence
from buster.repository.intelligence_service import RepositoryIntelligenceService
from buster.updater.manager import UpdateManager
from buster.version import VERSION
from buster.os_layer.os_layer import OSLayer
from buster.workspace.runtime import WorkspaceSnapshot
from buster.ai_state.state import AIStateStore

class BrainEngine:
    def __init__(self, services, bus, logger):
        self.services = services
        self.bus = bus
        self.logger = logger
        self.planner = AIPlanner()

    def process(self, text: str):
        cmd = text.strip().lower()
        AIStateStore().update(mode="thinking", last_command=text)

        if cmd in ["ai os state", "buster state", "brain state"]:
            return AIStateStore().report()


        if cmd in [
            "workspace",
            "workspace snapshot",
            "workspace status"
        ]:
            return WorkspaceSnapshot().snapshot()

        if cmd=="git branch":
            return WorkspaceSnapshot().git_branch()

        if cmd=="git status":
            return WorkspaceSnapshot().git_status()

        if cmd=="python info":
            return WorkspaceSnapshot().python_info()

        os_reply = OSLayer().handle(text)
        if os_reply is not None:
            return os_reply

        if cmd in ["check updates", "update status", "latest release"]:
            return UpdateManager(current_version=VERSION).status_text()

        repo_intel = RepositoryIntelligenceService(root=".")

        if cmd in ["index project", "reindex project", "index repository", "repo index"]:
            return repo_intel.index()

        if cmd in ["project summary", "project index", "codebase summary", "repository summary", "repo summary"]:
            return repo_intel.summary()

        if cmd in ["show todos", "show todo", "todos", "todo list"]:
            return repo_intel.todos()

        if cmd.startswith("find symbol "):
            return repo_intel.find_symbol(text[len("find symbol "):].strip())

        if cmd.startswith("find references "):
            return repo_intel.find_references(text[len("find references "):].strip())

        if cmd.startswith("imports of "):
            return repo_intel.imports_of(text[len("imports of "):].strip())

        if cmd.startswith("where is "):
            return repo_intel.where_is(text[len("where is "):].strip())

        if cmd in ["changed since index", "what changed since index"]:
            return repo_intel.changed_since_index()


        text = text.strip()
        if not text: return "I am online."
        self.services.get("memory").add("user", text)
        self.services.get("conversation").add_user(text)
        self.logger.info("User: " + text)
        plan = self.planner.make_plan(text)
        self.bus.emit("plan_updated", text=self.planner.describe())
        plan.status = "running"
        self.bus.emit("plan_updated", text=self.planner.describe())
        reply = self.execute(plan)
        plan.status = "done"
        self.bus.emit("plan_updated", text=self.planner.describe())
        self.services.get("memory").add("buster", reply)
        self.services.get("conversation").add_assistant(reply)
        AIStateStore().update(mode="idle", last_response=reply)
        return reply

    def execute(self, plan):
        s, a, target = self.services, plan.action, plan.target
        if a == "performance.status": return s.get("performance").report()
        if a == "services.status": return s.get("service_manager").status()
        if a == "threads.status": return s.get("thread_pool").status()
        if a == "tasks.list": return s.get("tasks").list_tasks()
        if a == "tasks.status": return s.get("tasks").status()
        if a == "workspace.status": return s.get("workspace").report()
        if a == "repo.index":
            task = s.get("tasks").submit("Index project", target or ".", s.get("repo").build, target or ".")
            return f"Repository indexing started as task #{task.id}."
        if a == "repo.status": return s.get("repo").status()
        if a == "repo.find_symbol": return s.get("repo").find_symbol(target)
        if a == "repo.where": return s.get("repo").where_is(target)
        if a == "repo.todos": return s.get("repo").todos()
        if a == "repo.largest": return s.get("repo").largest_files()
        if a == "knowledge.remember": return s.get("knowledge").remember(target)
        if a == "knowledge.recall": return s.get("knowledge").recall(target)
        if a == "knowledge.recall_all": return s.get("knowledge").recall("all")
        if a == "ai.status": return s.get("ai").status()
        if a == "ai.provider": return s.get("ai").set_provider(target)
        if a == "ai.answer": return s.get("ai").complete(target, context=self.build_context())
        if a == "apps.open": return s.get("apps").open(target)
        if a == "memory.search": return s.get("memory").search_text(target)
        if a == "system.status": return s.get("system").summary()
        if a == "agents.status": return s.get("agents").summary()
        if a == "automation.move_mouse": return s.get("automation").move_mouse_from_text(target)
        if a == "automation.type_text": return s.get("automation").type_text(target)
        if a == "automation.click": return s.get("automation").click()
        if a == "voice.status": return s.get("voice").status()
        if a == "voice.start": return s.get("voice").start_conversation()
        if a == "voice.stop": return s.get("voice").stop_conversation()
        if a == "voice.listen_once": return s.get("voice").listen_once_async()
        if a == "vision.status": return s.get("vision").status()
        if a == "vision.start":
            result = s.get("vision").start()
            self.bus.emit("show_vision_window")
            return result
        if a == "vision.stop": return s.get("vision").stop()
        if a == "vision.photo": return s.get("vision").take_photo()
        if a == "vision.faces": return s.get("vision").detect_faces()
        if a == "vision.objects": return s.get("vision").detect_objects()
        if a == "vision.qr": return s.get("vision").scan_qr()
        if a == "vision.ocr": return s.get("vision").read_text()
        if a == "vision.learn_face": return s.get("vision").learn_face(target or "Adam")
        if a == "vision.identify_face": return s.get("vision").identify_face()
        if a == "vision.face_status": return s.get("vision").face_status()
        if a == "plugins.status": return s.get("plugins").status()
        if a == "hardware.status": return s.get("hardware").status()
        if a == "diagnostics.report": return s.get("diagnostics").full_report()
        if a == "agents.delegate":
            if plan.agent == "builder":
                task = s.get("tasks").submit("Builder Agent", target, s.get("agents").delegate, plan.agent, target)
                return f"Builder task started as task #{task.id}. Use: task status"
            return s.get("agents").delegate(plan.agent, target)
        return s.get("ai").complete(target, context=self.build_context())

    def build_context(self):
        parts = []
        for getter in [
            lambda: self.services.get("system").summary(),
            lambda: self.services.get("apps").status(),
            lambda: "Knowledge:\n" + self.services.get("knowledge").recall("all"),
            lambda: "Repo:\n" + self.services.get("repo").status(),
            lambda: "Recent conversation:\n" + self.services.get("conversation").summary(),
        ]:
            try: parts.append(getter())
            except Exception: pass
        return "\n".join(parts)
