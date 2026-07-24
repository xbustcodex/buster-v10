# compiler.py
import os
import py_compile
import tempfile
from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot  # <-- Make sure Slot is added here
from typing import Any

class CodeCompiler:
    @staticmethod
    def check(code: str) -> tuple[bool, Optional[str]]:
        """Compiles code via py_compile inside a temporary file."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name

        try:
            py_compile.compile(temp_path, doraise=True)
            return True, None
        except py_compile.PyCompileError as e:
            return False, f"Compilation error: {e.msg}"
        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
                
    @Slot(object)
    def _verify_preview(self, value: Any = None) -> None:
        preview = PreviewDiff.from_value(
            value if value is not None else self._current_preview
        )

        if not preview.patch.strip():
            self.finding_details.set_action_output(
                "There is no preview available to verify."
            )
            return

        file_path = str(preview.file_path or "").strip()

        if not file_path:
            self.finding_details.set_preview_validation(
                "invalid",
                "The preview does not identify a file to verify.",
            )
            return

        if self._verification_worker is not None:
            self.finding_details.set_action_output(
                "Verification is already running."
            )
            return

        self._current_preview = preview

        self.finding_details.set_preview_busy(
            True,
            "Running python_agent syntax and compilation checks...",
        )
        self.status_label.setText("Running verification")

        # Try using python_agent syntax_checker & compiler directly
        try:
            from buster.agents.python_agent.syntax_checker import SyntaxChecker
            from buster.agents.python_agent.compiler import PythonCompiler

            checker = SyntaxChecker()
            compiler = PythonCompiler()

            # Execute verification on global threadpool
            worker = VerificationWorker(
                project_root=getattr(self.runtime_core, "root", "."),
                files=[file_path],
                change_id=str(preview.metadata.get("change_id", "")),
            )
        except ImportError:
            # Fallback to standard verification worker
            worker = VerificationWorker(
                project_root=getattr(self.runtime_core, "root", "."),
                files=[file_path],
                change_id=str(preview.metadata.get("change_id", "")),
            )

        worker.signals.progress.connect(self._verification_progress)
        worker.signals.finished.connect(
            lambda report, p=preview: self._verification_finished(report, p)
        )
        worker.signals.failed.connect(
            lambda message, p=preview: self._verification_failed(message, p)
        )

        self._verification_worker = worker
        QThreadPool.globalInstance().start(worker)            