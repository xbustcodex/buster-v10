import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CommandWorker(QThread):
    """Background worker to run CLI commands without freezing the UI."""
    finished_signal = Signal(str)

    def __init__(self, cmd, cwd):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd

    def run(self):
        try:
            result = subprocess.run(
                self.cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            self.finished_signal.emit(output)
        except Exception as e:
            self.finished_signal.emit(f"Error running command: {e}")


class ProjectPanel(QWidget):
    def __init__(self, live=None):
        super().__init__()
        self.live = live
        self.project_root = Path.cwd()
        self.worker = None

        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setWindowTitle("Project Explorer")
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        title = QLabel("📁 Project Explorer")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        # Main Info Display
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        # Monospace font for better alignment of stats and command outputs
        self.info.setFont(QFont("Monospace", 10))
        layout.addWidget(self.info, 1)

        # Action Buttons Layout
        buttons = QHBoxLayout()

        actions = [
            ("Refresh", self.refresh),
            ("Open Folder", self.open_folder),
            ("Index", self.index_project),
            ("Snapshot", self.snapshot_project),
            ("Run Tests", self.run_tests),
        ]

        for label, callback in actions:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            buttons.addWidget(btn)

        buttons.addStretch()
        layout.addLayout(buttons)

    def run_cmd_sync(self, cmd_args):
        """Helper for quick synchronous execution (e.g., git status)."""
        try:
            result = subprocess.run(
                cmd_args,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return (result.stdout + "\n" + result.stderr).strip()
        except Exception as e:
            return f"Error: {e}"

    def run_cmd_async(self, cmd_args, header_title):
        """Runs heavy tasks in a separate thread so UI stays responsive."""
        self.info.append(f"\n\n=== {header_title} (Running...) ===")
        
        self.worker = CommandWorker(cmd_args, self.project_root)
        self.worker.finished_signal.connect(
            lambda output: self.info.append(output or "Command completed with no output.")
        )
        self.worker.start()

    def git_branch(self):
        branch = self.run_cmd_sync(["git", "branch", "--show-current"])
        return branch if branch else "unknown / not a git repo"

    def git_status(self):
        status = self.run_cmd_sync(["git", "status", "--short"])
        return "Clean" if not status else status

    def count_files(self):
        skip = {
            ".git", "__pycache__", ".pytest_cache", ".lifecycle_backups",
            ".lifecycle_cache", ".lifecycle_logs", "dist", "build", "venv", ".venv"
        }

        count = 0
        py_files = 0
        tests = 0

        # Fast tree walk skipping excluded directories early
        for path in self.project_root.rglob("*"):
            if set(path.parts).intersection(skip):
                continue

            if path.is_file():
                count += 1
                if path.suffix == ".py":
                    py_files += 1
                    if path.name.startswith("test_"):
                        tests += 1

        return count, py_files, tests

    def refresh(self):
        files, py_files, tests = self.count_files()

        text = f"""==================================================
PROJECT INFORMATION
==================================================
Root Path:     {self.project_root}
Project Name:  {self.project_root.name}
Python Ver:    {sys.version.split()[0]}

GIT STATUS
--------------------------------------------------
Branch:        {self.git_branch()}
Status:        {self.git_status()}

STATISTICS
--------------------------------------------------
Total Files:   {files}
Python Files:  {py_files}
Test Files:    {tests}

ACTIONS OVERVIEW
--------------------------------------------------
[Refresh]      Reload project statistics & git info.
[Open Folder]  Switch active workspace root directory.
[Index]        Run test suite index diagnostics.
[Snapshot]     Log lightweight project breakdown.
[Run Tests]    Execute pytest suite in background thread.
"""
        self.info.setPlainText(text.strip())

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            str(self.project_root),
        )
        if folder:
            self.project_root = Path(folder)
            self.refresh()

    def index_project(self):
        cmd = [sys.executable, "-m", "pytest", "tests/test_imports.py", "-q"]
        self.run_cmd_async(cmd, "INDEX RESULT")

    def snapshot_project(self):
        files, py_files, tests = self.count_files()
        self.info.append("\n\n=== WORKSPACE SNAPSHOT ===")
        self.info.append(f"Project Name : {self.project_root.name}")
        self.info.append(f"Total Files  : {files}")
        self.info.append(f"Python Files : {py_files}")
        self.info.append(f"Test Files   : {tests}")

    def run_tests(self):
        cmd = [sys.executable, "-m", "pytest", "-q"]
        self.run_cmd_async(cmd, "TEST RESULT")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectPanel()
    window.show()
    sys.exit(app.exec())