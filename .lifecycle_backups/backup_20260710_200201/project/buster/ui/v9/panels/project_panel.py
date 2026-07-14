from pathlib import Path
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFileDialog,
)


class ProjectPanel(QWidget):
    def __init__(self, live=None):
        super().__init__()
        self.live = live
        self.project_root = Path.cwd()

        self.setWindowTitle("Project Explorer")
        self.resize(900, 650)

        layout = QVBoxLayout(self)

        title = QLabel("📁 Project Explorer")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        layout.addWidget(self.info, 1)

        buttons = QHBoxLayout()

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)

        open_folder = QPushButton("Open Folder")
        open_folder.clicked.connect(self.open_folder)

        index = QPushButton("Index")
        index.clicked.connect(self.index_project)

        snapshot = QPushButton("Snapshot")
        snapshot.clicked.connect(self.snapshot_project)

        test = QPushButton("Run Tests")
        test.clicked.connect(self.run_tests)

        buttons.addWidget(refresh)
        buttons.addWidget(open_folder)
        buttons.addWidget(index)
        buttons.addWidget(snapshot)
        buttons.addWidget(test)
        buttons.addStretch()

        layout.addLayout(buttons)

        self.refresh()

    def run_cmd(self, cmd):
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return (result.stdout + "\n" + result.stderr).strip()
        except Exception as e:
            return str(e)

    def git_branch(self):
        return self.run_cmd("git branch --show-current") or "unknown"

    def git_status(self):
        status = self.run_cmd("git status --short")
        return "Clean" if not status else status

    def count_files(self):
        skip = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".lifecycle_backups",
            ".lifecycle_cache",
            ".lifecycle_logs",
            "dist",
            "build",
            "venv",
            ".venv",
        }

        count = 0
        py_files = 0
        tests = 0

        for path in self.project_root.rglob("*"):
            if any(part in skip for part in path.parts):
                continue

            if path.is_file():
                count += 1

                if path.suffix == ".py":
                    py_files += 1

                if path.name.startswith("test_") and path.suffix == ".py":
                    tests += 1

        return count, py_files, tests

    def refresh(self):
        files, py_files, tests = self.count_files()

        text = f"""
PROJECT

Root:
{self.project_root}

Name:
{self.project_root.name}

Python:
{sys.version.split()[0]}

Git

Branch:
{self.git_branch()}

Status:
{self.git_status()}

Statistics

Files:
{files}

Python Files:
{py_files}

Test Files:
{tests}

Actions

Refresh:
Reload project information.

Open Folder:
Choose another project folder.

Index:
Placeholder for Repository Intelligence indexing.

Snapshot:
Placeholder for Workspace Snapshot.

Run Tests:
Runs pytest in the selected project.
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
        output = self.run_cmd("python -m pytest tests/test_imports.py -q")
        self.info.append("\n\nINDEX RESULT\n")
        self.info.append(output or "Index command completed.")

    def snapshot_project(self):
        files, py_files, tests = self.count_files()
        self.info.append("\n\nSNAPSHOT\n")
        self.info.append(f"Project: {self.project_root.name}")
        self.info.append(f"Files: {files}")
        self.info.append(f"Python files: {py_files}")
        self.info.append(f"Tests: {tests}")

    def run_tests(self):
        output = self.run_cmd("pytest -q")
        self.info.append("\n\nTEST RESULT\n")
        self.info.append(output or "pytest completed.")
