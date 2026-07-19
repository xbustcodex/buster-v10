
from __future__ import annotations
import time, uuid
from pathlib import Path
from typing import Iterable, Sequence

from .verification_report import VerificationReport
from .syntax_checker import SyntaxChecker
from .import_checker import ImportChecker
from .formatter_checker import FormatterChecker
from .lint_checker import LintChecker
from .unit_test_runner import UnitTestRunner
from .behavioral_checker import BehavioralChecker

class VerificationEngine:
    """Coordinates all verification stages into a single report."""

    def __init__(self, project_root:str|Path):
        self.project_root=Path(project_root).expanduser().resolve()
        self.syntax=SyntaxChecker(self.project_root)
        self.imports=ImportChecker(self.project_root)
        self.formatter=FormatterChecker(self.project_root)
        self.linter=LintChecker(self.project_root)
        self.tests=UnitTestRunner(self.project_root)
        self.behavior=BehavioralChecker(self.project_root)

    def verify(self,
               files:Iterable[str|Path],
               *,
               launch_command:Sequence[str]|None=None,
               change_id:str="")->VerificationReport:
        start=time.perf_counter()
        report=VerificationReport.create(
            report_id=str(uuid.uuid4()),
            change_id=change_id,
            project_root=str(self.project_root),
            target_files=[str(f) for f in files],
        )

        report.add_check(self.syntax.check(files,required=True))
        report.add_check(self.imports.check(files,required=True))
        report.add_check(self.formatter.check(files,required=False))
        report.add_check(self.linter.check(files,required=False))
        report.add_check(self.tests.check(required=False))

        if launch_command:
            report.add_check(
                self.behavior.check(
                    launch_command,
                    required=False,
                )
            )

        report.complete(time.perf_counter()-start)
        return report

__all__=["VerificationEngine"]
