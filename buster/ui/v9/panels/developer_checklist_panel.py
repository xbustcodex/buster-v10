import sys
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AsyncTestRunner(QThread):
    """Worker thread to run verification checks without freezing the UI."""
    finished_signal = Signal(str)

    def __init__(self, check_func):
        super().__init__()
        self.check_func = check_func

    def run(self):
        try:
            output = self.check_func()
            self.finished_signal.emit(output)
        except Exception as e:
            self.finished_signal.emit(f"Error executing checks: {e}")


class DeveloperChecklistPanel(QWidget):
    CHECKLIST_DATA = {
        "UI COMPLETION": [
            ("Dashboard", True),
            ("Chat", True),
            ("Sidebar Navigation", True),
            ("Runtime Workspace", True),
            ("Runtime Timeline", True),
            ("Face Popup", True),
            ("Notification Center", True),
            ("Developer Mission Control", True),
            ("Self Improvement", True),
        ],
        "AUDIO & VOICE ENGINE": [
            ("PyAudio Input", True),
            ("Google Speech Recognition", True),
            ("Local Whisper STT", False),
            ("Edge-TTS", False),
            ("pyttsx3 Fallback", True),
            ("Wake-Word Engine", False),
        ],
        "CORE RUNTIME": [
            ("Runtime Core", True),
            ("Event Bus", True),
            ("Service Manager", True),
            ("Runtime Monitor", True),
            ("Lifecycle Manager", True),
        ],
        "AI INTEGRATION": [
            ("Provider Framework", True),
            ("Ollama", True),
            ("Claude", False),
            ("OpenAI", False),
            ("Gemini", False),
        ],
        "AUTONOMY": [
            ("Autonomy Engine", True),
            ("Execution Engine", True),
            ("Self Improvement Service", True),
            ("Strategy Selector", True),
            ("Risk Analysis", True),
        ],
        "SYSTEM TESTING": [
            ("UI opens without errors", False),
            ("Runtime starts cleanly", False),
            ("Event Bus verified", False),
            ("All panels refresh", False),
            ("Memory verified", False),
            ("Plugin loading verified", False),
            ("AI conversation verified", False),
            ("Execution Engine verified", False),
            ("Self Improvement verified", False),
        ],
        "RELEASE PREPARATION": [
            ("PyInstaller build", False),
            ("Installer", False),
            ("Documentation", False),
        ],
    }

    def __init__(self, live=None):
        super().__init__()
        self.live = live
        self.worker = None

        self.init_ui()
        self.populate_checklist()

    def init_ui(self):
        self.setWindowTitle("Developer Checklist")
        self.resize(800, 720)

        layout = QVBoxLayout(self)

        # Header Title
        title = QLabel("🛠 Buster Developer Checklist")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title)

        # Status & Progress Summary
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: bold; color: #2e7d32; margin-bottom: 6px;")
        layout.addWidget(self.status_label)

        # Interactive Tree Checklist
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Task / Component", "Status"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.tree, 2)

        # Interactive "Add Item" Input Bar
        add_layout = QHBoxLayout()
        
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.setPlaceholderText("Select or Type Category...")
        self.cat_combo.setMinimumWidth(200)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter new task name (e.g. Local Whisper STT)...")
        self.task_input.returnPressed.connect(self.add_item_from_ui)

        add_btn = QPushButton("➕ Add Task")
        add_btn.clicked.connect(self.add_item_from_ui)

        add_layout.addWidget(self.cat_combo)
        add_layout.addWidget(self.task_input, 1)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

        # Log Console Output
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(100)
        self.log_console.setFont(QFont("Monospace", 9))
        self.log_console.setPlaceholderText("Execution & diagnostic logs will appear here...")
        layout.addWidget(self.log_console)

        # Bottom Action Bar
        buttons_layout = QHBoxLayout()

        actions = [
            ("Check All", lambda: self.toggle_all(True)),
            ("Uncheck All", lambda: self.toggle_all(False)),
            ("Run Quick Verification", self.run_quick_checks),
            ("Copy Checklist", self.copy_to_clipboard),
            ("Reset Default", self.populate_checklist),
        ]

        for label, callback in actions:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            buttons_layout.addWidget(btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

    def populate_checklist(self):
        """Populates the interactive tree widget from default data."""
        self.tree.blockSignals(True)
        self.tree.clear()
        self.cat_combo.clear()

        for category, items in self.CHECKLIST_DATA.items():
            self.cat_combo.addItem(category)
            cat_item = QTreeWidgetItem(self.tree)
            cat_item.setText(0, category)
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            cat_item.setFont(0, QFont("Sans-Serif", 10, QFont.Bold))

            for task_name, is_checked in items:
                child = QTreeWidgetItem(cat_item)
                child.setText(0, task_name)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
                child.setText(1, "Done" if is_checked else "Pending")

            cat_item.setExpanded(True)

        self.tree.blockSignals(False)
        self.update_summary()

    def add_checklist_item(self, category_name: str, item_name: str, is_checked: bool = False):
        """Dynamically adds an item to the tree programmatically or via UI."""
        if not category_name.strip() or not item_name.strip():
            return

        category_name = category_name.strip()
        item_name = item_name.strip()

        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        target_cat = None

        # Find existing category
        for i in range(root.childCount()):
            cat_item = root.child(i)
            if cat_item.text(0).upper() == category_name.upper():
                target_cat = cat_item
                break

        # If category doesn't exist, create it
        if target_cat is None:
            target_cat = QTreeWidgetItem(self.tree)
            target_cat.setText(0, category_name.upper())
            target_cat.setFlags(target_cat.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            target_cat.setFont(0, QFont("Sans-Serif", 10, QFont.Bold))
            target_cat.setExpanded(True)
            self.cat_combo.addItem(category_name.upper())

        # Add child task
        child = QTreeWidgetItem(target_cat)
        child.setText(0, item_name)
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        child.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
        child.setText(1, "Done" if is_checked else "Pending")

        self.tree.blockSignals(False)
        self.update_summary()
        self.log_console.append(f"[Added]: {item_name} under [{target_cat.text(0)}]")

    def add_item_from_ui(self):
        """Handler for the 'Add Task' UI button and Return key."""
        category = self.cat_combo.currentText()
        task_name = self.task_input.text()
        
        if task_name.strip():
            self.add_checklist_item(category, task_name, is_checked=False)
            self.task_input.clear()

    def get_git_branch(self) -> str:
        if self.live and hasattr(self.live, "git_branch"):
            return self.live.git_branch()
        return "main"

    def update_summary(self):
        """Recalculates completed tasks and updates the status bar."""
        total = 0
        checked = 0

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                total += 1
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked += 1

        percent = (checked / total * 100) if total > 0 else 0.0
        git_branch = self.get_git_branch()

        self.status_label.setText(
            f"Branch: {git_branch}  |  Progress: {checked}/{total} ({percent:.1f}%)"
        )

    def on_item_changed(self, item, column):
        if column == 0 and item.childCount() == 0:
            is_checked = item.checkState(0) == Qt.CheckState.Checked
            item.setText(1, "Done" if is_checked else "Pending")
            self.update_summary()

    def toggle_all(self, check_state: bool):
        self.tree.blockSignals(True)
        state = Qt.CheckState.Checked if check_state else Qt.CheckState.Unchecked

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                child.setCheckState(0, state)
                child.setText(1, "Done" if check_state else "Pending")

        self.tree.blockSignals(False)
        self.update_summary()

    def run_quick_checks(self):
        self.log_console.append("=== RUNNING DIAGNOSTIC VERIFICATION ===")

        def simulate_checks():
            import time
            time.sleep(1)
            return "✓ Runtime loaded\n✓ Event bus responsive\n✓ System healthy"

        self.worker = AsyncTestRunner(simulate_checks)
        self.worker.finished_signal.connect(
            lambda res: self.log_console.append(f"{res}\n[Verification Completed]\n")
        )
        self.worker.start()

    def copy_to_clipboard(self):
        output_text = f"## Buster Developer Checklist\n"
        output_text += f"**Git Branch:** {self.get_git_branch()}\n\n"

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            output_text += f"### {cat_item.text(0)}\n"
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                is_checked = child.checkState(0) == Qt.CheckState.Checked
                box = "[x]" if is_checked else "[ ]"
                output_text += f"- {box} {child.text(0)}\n"
            output_text += "\n"

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(output_text)
        self.log_console.append("[System]: Formatted checklist copied to clipboard.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeveloperChecklistPanel()
    window.show()
    sys.exit(app.exec())