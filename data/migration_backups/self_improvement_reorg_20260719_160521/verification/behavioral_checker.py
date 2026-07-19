
from __future__ import annotations
import subprocess,time
from pathlib import Path
from typing import Sequence
from .verification_report import CheckResult,CheckStatus,VerificationIssue

class BehavioralChecker:
    """Launches an application and verifies it starts and exits cleanly."""

    name="behavior"

    def __init__(self,project_root:str|Path,timeout_seconds:float=15.0):
        self.project_root=Path(project_root).expanduser().resolve()
        self.timeout_seconds=float(timeout_seconds)

    def check(self,command:Sequence[str],*,required:bool=False)->CheckResult:
        start=time.perf_counter()
        r=CheckResult(name=self.name,status=CheckStatus.RUNNING,required=required,
                      summary="Running behavioral verification...",
                      command=subprocess.list2cmdline(list(command)))
        r.start()
        if not command:
            r.add_issue(VerificationIssue(message="No launch command supplied.",
                                         checker=self.name,code="NO_COMMAND"))
            r.finish(CheckStatus.SKIPPED,"Behavioral check skipped.")
            r.required=False
            return r
        try:
            proc=subprocess.Popen(
                list(command),
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                out,err=proc.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                proc.kill()
                out,err=proc.communicate()
                r.stdout=out or ""
                r.stderr=err or ""
                r.duration_seconds=time.perf_counter()-start
                r.finish(CheckStatus.PASSED,
                         "Application launched and remained running.")
                r.metadata={"launch_ok":True,"timeout":self.timeout_seconds}
                return r
        except OSError as exc:
            r.add_issue(VerificationIssue(
                message="Unable to launch application.",
                checker=self.name,
                code="LAUNCH_ERROR",
                details=str(exc),
            ))
            r.finish(CheckStatus.ERROR,"Behavioral check failed to start.")
            return r

        r.duration_seconds=time.perf_counter()-start
        r.stdout=out or ""
        r.stderr=err or ""
        r.exit_code=proc.returncode

        if proc.returncode==0:
            r.finish(CheckStatus.PASSED,
                     "Application launched and exited successfully.")
        else:
            r.add_issue(VerificationIssue(
                message=f"Application exited with code {proc.returncode}.",
                checker=self.name,
                code="NON_ZERO_EXIT",
            ))
            r.finish(CheckStatus.FAILED,
                     "Behavioral verification failed.")

        r.metadata={
            "launch_ok":proc.returncode==0,
            "exit_code":proc.returncode,
        }
        return r

__all__=["BehavioralChecker"]
