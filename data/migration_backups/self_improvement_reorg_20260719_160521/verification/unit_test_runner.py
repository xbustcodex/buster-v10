
from __future__ import annotations
import shutil, subprocess, sys, time
from pathlib import Path
from typing import Iterable
from .verification_report import CheckResult, CheckStatus, VerificationIssue

class UnitTestRunner:
    """Runs pytest as part of the verification pipeline."""

    name="unit_tests"

    def __init__(self, project_root:str|Path, timeout_seconds:float=300.0):
        self.project_root=Path(project_root).expanduser().resolve()
        self.timeout_seconds=float(timeout_seconds)

    def check(self, targets:Iterable[str|Path]|None=None, *, required:bool=False)->CheckResult:
        start=time.perf_counter()
        cmd=self._command(targets)
        if cmd is None:
            return CheckResult.skipped_result(
                self.name,
                "pytest is not installed.",
                required=False,
                duration_seconds=time.perf_counter()-start,
                metadata={"runner":"pytest","available":False},
            )

        result=CheckResult(
            name=self.name,
            status=CheckStatus.RUNNING,
            required=required,
            summary="Running unit tests...",
            command=subprocess.list2cmdline(cmd),
        )
        result.start()

        try:
            cp=subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            result.add_issue(VerificationIssue(
                message="Unit tests timed out.",
                checker=self.name,
                code="TEST_TIMEOUT",
            ))
            result.finish(CheckStatus.ERROR,"Unit test execution timed out.")
            return result

        result.duration_seconds=time.perf_counter()-start
        result.exit_code=cp.returncode
        result.stdout=cp.stdout or ""
        result.stderr=cp.stderr or ""

        if cp.returncode==0:
            result.finish(CheckStatus.PASSED,"All unit tests passed.")
        elif cp.returncode==5:
            result.finish(CheckStatus.SKIPPED,"No unit tests were collected.")
            result.required=False
        else:
            self._extract_failures(result)
            result.finish(CheckStatus.FAILED,"One or more unit tests failed.")

        result.metadata={
            "runner":"pytest",
            "available":True,
            "targets":list(str(t) for t in (targets or [])),
        }
        return result

    def check_path(self,path:str|Path,*,required:bool=False)->CheckResult:
        return self.check([path],required=required)

    def _command(self,targets):
        exe=shutil.which("pytest")
        if exe:
            cmd=[exe,"-q"]
        else:
            try:
                import pytest # noqa
            except Exception:
                return None
            cmd=[sys.executable,"-m","pytest","-q"]
        if targets:
            cmd.extend(str(Path(t)) for t in targets)
        return cmd

    def _extract_failures(self,result:CheckResult):
        for line in (result.stdout+"\n"+result.stderr).splitlines():
            s=line.strip()
            if s.startswith("FAILED ") or s.startswith("ERROR "):
                result.add_issue(VerificationIssue(
                    message=s,
                    severity="error",
                    checker=self.name,
                    code="TEST_FAILURE",
                ))

__all__=["UnitTestRunner"]
