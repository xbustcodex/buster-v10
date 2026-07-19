
from __future__ import annotations
import shutil, subprocess, sys, time
from pathlib import Path
from typing import Iterable, Optional
from .verification_report import CheckResult, CheckStatus, VerificationIssue

class LintChecker:
    """Runs Ruff in check mode without modifying files."""
    name="lint"
    def __init__(self, project_root:str|Path, timeout_seconds:float=60.0)->None:
        self.project_root=Path(project_root).expanduser().resolve()
        self.timeout_seconds=timeout_seconds

    def check(self, files:Iterable[str|Path], *, required:bool=False)->CheckResult:
        start=time.perf_counter()
        targets=[p for p in self._resolve(files) if p.suffix.lower()==".py"]
        if not targets:
            return CheckResult.skipped_result(self.name,"No Python files to lint.",required=False,
                duration_seconds=time.perf_counter()-start,metadata={"linter":"ruff"})
        cmd=self._cmd(targets)
        if cmd is None:
            return CheckResult.skipped_result(self.name,"Ruff is not installed.",required=False,
                duration_seconds=time.perf_counter()-start,metadata={"linter":"ruff","available":False})
        r=CheckResult(name=self.name,status=CheckStatus.RUNNING,required=required,command=subprocess.list2cmdline(cmd))
        r.start()
        try:
            cp=subprocess.run(cmd,cwd=self.project_root,capture_output=True,text=True,timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            r.add_issue(VerificationIssue(message="Lint timed out.",checker=self.name,code="LINT_TIMEOUT"))
            r.finish(CheckStatus.ERROR,"Lint timed out.")
            return r
        r.duration_seconds=time.perf_counter()-start
        r.exit_code=cp.returncode
        r.stdout=cp.stdout or ""
        r.stderr=cp.stderr or ""
        if cp.returncode==0:
            r.finish(CheckStatus.PASSED,f"Lint passed for {len(targets)} file(s).")
        elif cp.returncode==1:
            self._parse(cp.stdout+("\n"+cp.stderr if cp.stderr else ""),r)
            r.finish(CheckStatus.FAILED,f"{len(r.issues)} lint issue(s) found.")
        else:
            r.add_issue(VerificationIssue(message="Ruff execution error.",checker=self.name,code="LINT_ERROR",details=r.stderr))
            r.finish(CheckStatus.ERROR,"Lint failed to execute.")
        r.metadata={"checked_files":len(targets),"linter":"ruff","available":True}
        return r

    def check_file(self,file_path:str|Path,*,required:bool=False)->CheckResult:
        return self.check([file_path],required=required)

    def _cmd(self,targets):
        exe=shutil.which("ruff")
        if exe:
            cmd=[exe,"check"]
        else:
            try:
                import ruff # noqa
            except Exception:
                return None
            cmd=[sys.executable,"-m","ruff","check"]
        cmd.extend(str(p) for p in targets)
        return cmd

    def _parse(self,text:str,result:CheckResult):
        for line in text.splitlines():
            if ":" not in line: continue
            parts=line.split(":",3)
            if len(parts)<4: continue
            f,l,c,msg=parts
            try:
                line_no=int(l); col=int(c)
            except:
                continue
            result.add_issue(VerificationIssue(
                message=msg.strip(),severity="error",file=f,
                line=line_no,column=col,checker=self.name,code="LINT"))

    def _resolve(self,files):
        seen=set(); out=[]
        for v in files:
            p=Path(v).expanduser()
            if not p.is_absolute(): p=self.project_root/p
            p=p.resolve()
            k=str(p).lower()
            if k in seen: continue
            seen.add(k); out.append(p)
        return out

__all__=["LintChecker"]
