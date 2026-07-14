from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton, QTextEdit, QLineEdit, QProgressBar, QScrollArea
from buster.ui.themes.dark import DARK_STYLE
from buster.ui.widgets.panel import Panel
from buster.ui.widgets.face import FaceWidget
from buster.ui.widgets.service_card import ServiceCard
from buster.ui.widgets.vision_window import VisionWindow
from buster.ui.settings_dialog import SettingsDialog
from buster.core.settings_store import SettingsStore



class UiBridge(QObject):
    voice_command = Signal(str)
    voice_status = Signal(str)
    plan_updated = Signal(str)
    show_vision = Signal()
    brain_result = Signal(str, str)

class MainWindow(QMainWindow):
    def __init__(self, settings, state, services, bus):
        super().__init__()
        self.settings, self.state, self.services, self.bus = settings, state, services, bus
        SettingsStore().load_into(self.settings)
        self.vision_window = VisionWindow(self.services.get("vision"))
        self.bridge = UiBridge()
        self.bridge.voice_command.connect(self.handle_voice_command)
        self.bridge.voice_status.connect(self.handle_voice_status)
        self.bridge.plan_updated.connect(self.on_plan_updated)
        self.bridge.show_vision.connect(self.show_vision_window)
        self.bridge.brain_result.connect(self.handle_brain_result)
        self.bus.on("plan_updated", lambda text: self.bridge.plan_updated.emit(text))
        self.bus.on("show_vision_window", lambda: self.bridge.show_vision.emit())
        self.bus.on("voice_command", lambda text: self.bridge.voice_command.emit(text))
        self.bus.on("voice_status", lambda status: self.bridge.voice_status.emit(status))
        flags = Qt.Window | (Qt.WindowStaysOnTopHint if settings.always_on_top else Qt.WindowType(0))
        self.setWindowFlags(flags)
        self.setWindowTitle(f"{settings.app_name} {settings.version}")
        self.resize(settings.main_width, settings.main_height)
        self.setStyleSheet(DARK_STYLE)
        self.build()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)
        self.refresh()

    def make_scroll_panel(self, inner_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner_widget)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: 0px; background: #050b12; }")
        return scroll

    def build(self):
        root = QWidget(); self.setCentralWidget(root); outer = QHBoxLayout(root)
        side = QVBoxLayout()
        title = QLabel(f"{self.settings.app_name} {self.settings.version}"); title.setObjectName("Title"); side.addWidget(title)
        for label, cmd in [
            ("Workspace","workspace"),
            ("Performance","performance"),
            ("Tasks","tasks"),
            ("Index Project","index project"),
            ("Repo Status","repo status"),
            ("AI Status","ai status"),
            ("Use Local","use local"),
            ("Use Ollama","use ollama"),
            ("Listen Once","listen once"),
            ("Conversation","start conversation"),
            ("Browser","open my browser"),
            ("Vision","start vision"),
            ("Agents","agents"),
            ("Settings","settings"),          # NEW
            ("System","system status")
]:
            b = QPushButton(label); b.clicked.connect(lambda checked=False, c=cmd: self.run_command(c)); side.addWidget(b)
        side.addStretch(); compact = QPushButton("Compact"); compact.clicked.connect(self.toggle_compact); side.addWidget(compact)

        grid = QGridLayout()
        face_panel = Panel(); fl = QVBoxLayout(face_panel); self.face = FaceWidget(); self.mode = QLabel("STANDBY"); self.mode.setObjectName("Section"); self.mode.setAlignment(Qt.AlignCenter); fl.addWidget(self.face, 1); fl.addWidget(self.mode)

        planner_panel = Panel(); pl = QVBoxLayout(planner_panel); pt = QLabel("AI PLANNER"); pt.setObjectName("Section")
        self.plan_box = QTextEdit(); self.plan_box.setReadOnly(True); self.plan_box.setPlainText("Waiting for command...")
        self.input = QLineEdit(); self.input.setPlaceholderText("Try: workspace, remember my browser is Firefox, index project, builder create a weather app"); self.input.returnPressed.connect(self.send)
        pl.addWidget(pt); pl.addWidget(self.plan_box); pl.addWidget(self.input)

        chat_panel = Panel(); cl = QVBoxLayout(chat_panel); ct = QLabel("CHAT"); ct.setObjectName("Section"); self.chat = QTextEdit(); self.chat.setReadOnly(True); cl.addWidget(ct); cl.addWidget(self.chat)

        sys_panel = Panel(); sl = QVBoxLayout(sys_panel); st = QLabel("SYSTEM"); st.setObjectName("Section"); sl.addWidget(st); self.sys_bars = {}
        for key in ["cpu","ram","disk"]:
            row = QHBoxLayout(); row.addWidget(QLabel(key.upper())); bar = QProgressBar(); bar.setRange(0,100); val = QLabel("0%"); row.addWidget(bar); row.addWidget(val); sl.addLayout(row); self.sys_bars[key] = (bar, val)

        agent_panel = Panel(); al = QVBoxLayout(agent_panel); at = QLabel("AGENT WORKERS"); at.setObjectName("Section"); al.addWidget(at); self.agent_bars = {}
        for name in self.services.get("agents").snapshot():
            row = QHBoxLayout(); row.addWidget(QLabel(name)); bar = QProgressBar(); bar.setRange(0,100); val = QLabel("Ready"); row.addWidget(bar); row.addWidget(val); al.addLayout(row); self.agent_bars[name] = (bar,val)

        services_panel = Panel(); sv = QVBoxLayout(services_panel); svt = QLabel("SERVICE CARDS"); svt.setObjectName("Section"); sv.addWidget(svt)
        self.cards = {k: ServiceCard(k) for k in ["Brain","AI","Tasks","Repo","Voice","Vision","Performance","Threads","Plugins","Hardware"]}
        for c in self.cards.values(): sv.addWidget(c)
        sv.addStretch()

        mem_panel = Panel(); ml = QVBoxLayout(mem_panel); mt = QLabel("RECENT MEMORY"); mt.setObjectName("Section"); self.memory_box = QTextEdit(); self.memory_box.setReadOnly(True); ml.addWidget(mt); ml.addWidget(self.memory_box)
        grid.addWidget(face_panel,0,0,2,1); grid.addWidget(planner_panel,0,1,1,1); grid.addWidget(chat_panel,1,1,1,1); grid.addWidget(sys_panel,2,0); grid.addWidget(agent_panel,2,1); grid.addWidget(self.make_scroll_panel(services_panel),3,0); grid.addWidget(mem_panel,3,1)
        grid.setRowStretch(0,3); grid.setRowStretch(1,2); grid.setRowStretch(2,1); grid.setRowStretch(3,3); grid.setColumnStretch(0,3); grid.setColumnStretch(1,2)
        outer.addLayout(side,1); outer.addLayout(grid,5)

    def handle_voice_status(self, status):
        if status in ["listening","calibrating","recognizing","conversation"]: self.set_mode("listening")
        elif status in ["standby","stopped"]: self.set_mode("standby")
        elif status == "error": self.set_mode("error")

    def handle_voice_command(self, text):
        if text: self.chat.append(f"Heard: {text}"); self.run_command(text)
        else: self.chat.append("Buster: I did not hear a command clearly."); self.services.get("voice").speak("I did not hear that clearly."); self.set_mode("standby")

    def show_vision_window(self): self.vision_window.show(); self.vision_window.raise_()
    def on_plan_updated(self, text): self.plan_box.setPlainText(text)
    def send(self):
        text = self.input.text().strip()
        if text: self.input.clear(); self.run_command(text)

    def run_command(self, text):
        self.chat.append(f"You: {text}"); self.set_mode("thinking")
        cmd = text.strip().lower()

        if cmd in ["settings", "open settings"]:
            dlg = SettingsDialog(self.settings, self)

            if dlg.exec():
                values = dlg.get_values()

                self.settings.always_on_top = values["always_on_top"]
                self.settings.wake_word = values["wake_word"]
                self.settings.data_dir = values["data_dir"]
                self.settings.logs_dir = values["logs_dir"]
                self.settings.screenshots_dir = values["screenshots_dir"]

                store = SettingsStore()
                store.save(self.settings)

                self.chat.append(
                    f"Buster: Settings saved.\n{store.path.resolve()}"
                )

            self.set_mode("standby")
            return
        
        main_thread_commands = {"start vision","show vision","open vision","start camera","show camera","open camera","stop vision","hide vision","stop camera"}
        if text.strip().lower() in main_thread_commands:
            try: reply = self.services.get("brain").process(text)
            except Exception as exc: reply = f"Command failed: {exc}"
            self.handle_brain_result(text, reply); return
        def worker():
            try: reply = self.services.get("brain").process(text)
            except Exception as exc: reply = f"Command failed: {exc}"
            self.bridge.brain_result.emit(text, reply)
        self.services.get("thread_pool").submit(worker)

    def handle_brain_result(self, text, reply):
        self.chat.append(f"Buster: {reply}"); self.services.get("voice").speak(reply)
        if "Listening once" in reply or "Conversation mode started" in reply: self.set_mode("listening")
        else: self.set_mode("speaking"); QTimer.singleShot(1400, lambda: self.set_mode("standby"))
        self.refresh()

    def set_mode(self, mode):
        self.state.set_mode(mode); self.face.set_state(mode); self.mode.setText(mode.upper())

    def refresh(self):
        s = self.services.get("system").snapshot()
        for key, (bar, val) in self.sys_bars.items(): bar.setValue(s[key]); val.setText(f"{s[key]}%")
        for name, data in self.services.get("agents").snapshot().items():
            bar, val = self.agent_bars[name]; bar.setValue(data["progress"]); val.setText(f"{data['status']} - {data['task'][:24]}")
        self.cards["Brain"].set_status("ONLINE"); self.cards["AI"].set_status(self.services.get("ai").quick_status()); self.cards["Tasks"].set_status(self.services.get("tasks").summary())
        self.cards["Repo"].set_status(self.services.get("repo").status().replace("\n"," | ")[:180]); self.cards["Voice"].set_status(self.services.get("voice").status()); self.cards["Vision"].set_status(self.services.get("vision").status())
        perf = self.services.get("performance").snapshot(); self.cards["Performance"].set_status(f"CPU {perf['system_cpu']}% RAM {perf['process_ram_mb']}MB")
        self.cards["Threads"].set_status(self.services.get("thread_pool").status()); self.cards["Plugins"].set_status(self.services.get("plugins").status()); self.cards["Hardware"].set_status(self.services.get("hardware").status())
        self.memory_box.setPlainText("\n".join(self.services.get("memory").recent_clean(10)))

    def toggle_compact(self):
        self.state.compact = not self.state.compact
        self.resize(self.settings.compact_width if self.state.compact else self.settings.main_width, self.settings.compact_height if self.state.compact else self.settings.main_height)
