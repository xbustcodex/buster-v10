from pathlib import Path
import shutil
import subprocess
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QListWidget,
    QLineEdit,
    QMessageBox,
)


class WorkspacePanel(QWidget):
    def __init__(self, live=None, runtime_core=None):
        super().__init__()
        self.live = live
        self.workspace_root = Path.cwd() / "buster_workspace" / "ai_builds"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("AI Build Workspace")
        self.resize(950, 680)

        layout = QVBoxLayout(self)

        title = QLabel("🧠 AI Build Workspace")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Describe what Buster should build...")
        layout.addWidget(self.task_input)

        buttons = QHBoxLayout()

        create_task = QPushButton("Create Task Workspace")
        create_task.clicked.connect(self.create_task_workspace)

        open_folder = QPushButton("Open Folder")
        open_folder.clicked.connect(self.open_selected_folder)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)

        snapshot = QPushButton("Snapshot")
        snapshot.clicked.connect(self.snapshot_selected)

        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete_selected)

        buttons.addWidget(create_task)
        buttons.addWidget(open_folder)
        buttons.addWidget(snapshot)
        buttons.addWidget(delete)
        buttons.addWidget(refresh)
        buttons.addStretch()

        layout.addLayout(buttons)

        body = QHBoxLayout()

        self.tasks = QListWidget()
        self.tasks.currentTextChanged.connect(self.show_task)

        self.details = QTextEdit()
        self.details.setReadOnly(True)

        body.addWidget(self.tasks, 1)
        body.addWidget(self.details, 2)

        layout.addLayout(body, 1)

        self.refresh()

    def task_path(self, name):
        return self.workspace_root / name

    def safe_name(self, text):
        base = "".join(c.lower() if c.isalnum() else "_" for c in text)
        base = "_".join(part for part in base.split("_") if part)
        return base[:40] or "task"

    def create_task_workspace(self):
        task = self.task_input.text().strip()
        if not task:
            task = "New build task"

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"task_{stamp}_{self.safe_name(task)}"
        path = self.task_path(folder_name)
        path.mkdir(parents=True, exist_ok=True)

        (path / "README.md").write_text(
            f"# {task}\n\n"
            f"Created: {datetime.now().isoformat()}\n\n"
            "## Status\n\n"
            "- planning\n\n"
            "## Notes\n\n"
            "This is an isolated AI build workspace. "
            "Files should be created here before being merged into the main project.\n",
            encoding="utf-8",
        )

        (path / "src").mkdir(exist_ok=True)
        (path / "tests").mkdir(exist_ok=True)

        self.task_input.clear()
        self.refresh()
        self.tasks.setCurrentRow(0)

    def refresh(self):
        self.tasks.clear()

        folders = sorted(
            [p for p in self.workspace_root.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for folder in folders:
            self.tasks.addItem(folder.name)

        if folders:
            self.tasks.setCurrentRow(0)
        else:
            self.details.setPlainText(
                "No AI build workspaces yet.\n\n"
                "Describe something for Buster to build, then click Create Task Workspace."
            )

    def show_task(self, name):
        if not name:
            return

        path = self.task_path(name)
        if not path.exists():
            return

        files = [p for p in path.rglob("*") if p.is_file()]
        py_files = [p for p in files if p.suffix == ".py"]
        test_files = [p for p in files if p.name.startswith("test_")]

        readme = path / "README.md"
        readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""

        self.details.setPlainText(
            f"WORKSPACE\n\n"
            f"Name:\n{name}\n\n"
            f"Path:\n{path}\n\n"
            f"Files:\n{len(files)}\n\n"
            f"Python Files:\n{len(py_files)}\n\n"
            f"Tests:\n{len(test_files)}\n\n"
            f"README\n\n{readme_text}"
        )

    def selected_path(self):
        item = self.tasks.currentItem()
        if not item:
            return None
        return self.task_path(item.text())

    def open_selected_folder(self):
        path = self.selected_path()
        if not path:
            return

        subprocess.Popen(f'explorer "{path}"')

    def snapshot_selected(self):
        path = self.selected_path()
        if not path:
            return

        files = [p for p in path.rglob("*") if p.is_file()]
        snapshot = path / "SNAPSHOT.txt"
        snapshot.write_text(
            "AI BUILD WORKSPACE SNAPSHOT\n\n"
            f"Workspace: {path.name}\n"
            f"Created: {datetime.now().isoformat()}\n"
            f"Files: {len(files)}\n\n"
            + "\n".join(str(p.relative_to(path)) for p in files),
            encoding="utf-8",
        )

        self.show_task(path.name)

    def delete_selected(self):
        path = self.selected_path()
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Delete Workspace",
            f"Delete workspace?\n\n{path.name}",
        )

        if reply == QMessageBox.Yes:
            shutil.rmtree(path)
            self.refresh()