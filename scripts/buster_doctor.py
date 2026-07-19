from __future__ import annotations

import importlib
import json
import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "OK"

    @property
    def warn(self) -> bool:
        return self.status == "WARN"

    @property
    def fail(self) -> bool:
        return self.status == "FAIL"


class BusterDoctor:
    def __init__(self, auto_fix: bool = False, run_tests: bool = True):
        self.auto_fix = auto_fix
        self.run_tests = run_tests
        self.results: List[CheckResult] = []

    def add(self, name: str, status: str, detail: str = ""):
        self.results.append(CheckResult(name, status, detail))

    def run_cmd(self, args: list[str], timeout: int = 12) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                args,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except Exception as exc:
            return 999, "", str(exc)

    def check_python(self):
        version = sys.version.split()[0]
        self.add("Python", "OK", f"{version} ({platform.system()} {platform.release()})")

    def check_git(self):
        code, out, err = self.run_cmd(["git", "--version"])
        if code == 0:
            self.add("Git", "OK", out)
        else:
            self.add("Git", "FAIL", err or "git not found")
            return

        code, out, err = self.run_cmd(["git", "branch", "--show-current"])
        branch = out or "unknown"

        code, out, err = self.run_cmd(["git", "status", "--porcelain"])
        if code == 0:
            clean = "clean" if not out.strip() else "changes present"
            self.add("Git Branch", "OK", f"{branch} ({clean})")
        else:
            self.add("Git Branch", "WARN", err or "could not read git status")

    def check_internet_dependencies(self):
        required = [
            "requests",
            "bs4",
        ]
        for module in required:
            try:
                importlib.import_module(module)
                self.add(f"Python module: {module}", "OK", "installed")
            except Exception as exc:
                self.add(f"Python module: {module}", "FAIL", str(exc))

    def check_voice_dependencies(self):
        modules = [
            ("speech_recognition", "SpeechRecognition"),
            ("pyaudio", "PyAudio"),
        ]
        for module, label in modules:
            try:
                importlib.import_module(module)
                self.add(f"Voice dependency: {label}", "OK", "installed")
            except Exception as exc:
                self.add(f"Voice dependency: {label}", "FAIL", str(exc))

    def check_network(self):
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3).close()
            self.add("Network", "OK", "internet reachable")
        except Exception as exc:
            self.add("Network", "WARN", f"internet check failed: {exc}")

    def check_ollama(self):
        code, out, err = self.run_cmd(["ollama", "list"], timeout=8)
        if code != 0:
            self.add("Ollama", "WARN", err or "ollama command unavailable")
            return

        lines = out.splitlines()
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])

        if models:
            self.add("Ollama", "OK", f"models installed: {', '.join(models)}")
            preferred = next((m for m in models if "coder" in m.lower()), models[0])
            self.add("Ollama selected model", "OK", preferred)
        else:
            self.add("Ollama", "WARN", "running/installed but no models found")

        code, out, err = self.run_cmd(["ollama", "ps"], timeout=8)
        if code == 0 and out.strip():
            self.add("Ollama loaded models", "OK", out.splitlines()[0] if out else "none")
        else:
            self.add("Ollama loaded models", "WARN", "no model currently loaded")

    def check_buster_files(self):
        required = [
            "buster/web/internet_service.py",
            "buster/brain/tool_router.py",
            "buster/brain/orchestrator.py",
            "buster/brain/providers/ai_modes.py",
            "buster/brain/providers/ollama.py",
            "buster/voice/latency_config.py",
            "buster/voice/voice_pipeline.py",
            "data/web_cache.json",
            "data/web_knowledge_cache.json",
            "buster/ui/v9/face_window.py",
            "buster/core/runtime.py",
            "buster/ui/v9/main_window.py",
        ]
        for rel in required:
            path = ROOT / rel
            self.add(f"File: {rel}", "OK" if path.exists() else "FAIL", "found" if path.exists() else "missing")

    def check_data_dirs(self):
        for rel in ["data", "logs", "backups", "scripts", "tests"]:
            path = ROOT / rel
            if path.exists():
                self.add(f"Directory: {rel}", "OK", "found")
            else:
                if self.auto_fix:
                    path.mkdir(parents=True, exist_ok=True)
                    self.add(f"Directory: {rel}", "OK", "created")
                else:
                    self.add(f"Directory: {rel}", "WARN", "missing")

    def check_pytest(self):
        if not self.run_tests:
            self.add("Pytest", "WARN", "skipped")
            return

        code, out, err = self.run_cmd([sys.executable, "-m", "pytest"], timeout=120)
        combined = (out + "\n" + err).strip()
        last_line = ""
        for line in combined.splitlines()[::-1]:
            if "passed" in line or "failed" in line or "error" in line.lower():
                last_line = line.strip()
                break

        if code == 0:
            self.add("Pytest", "OK", last_line or "tests passed")
        else:
            self.add("Pytest", "FAIL", last_line or "tests failed")

    def check_provider_diagnostics(self):
        try:
            from buster.brain.providers.provider_diagnostics import ProviderDiagnostics
            report = ProviderDiagnostics().report().replace("\n", " | ")
            self.add("AI Provider Diagnostics", "OK", report[:240])
        except Exception as exc:
            self.add("AI Provider Diagnostics", "WARN", str(exc))

    def check_import_core_modules(self):
        modules = [
            "buster.web.internet_service",
            "buster.brain.tool_router",
            "buster.brain.orchestrator",
            "buster.brain.providers.ai_modes",
            "buster.brain.providers.ollama",
            "buster.voice.voice_pipeline",
        ]
        for module in modules:
            try:
                importlib.import_module(module)
                self.add(f"Import: {module}", "OK", "imported")
            except Exception as exc:
                self.add(f"Import: {module}", "FAIL", str(exc))
                
    def check_runtime(self):
        try:
            from buster.runtime.core import create_runtime_core

            core = create_runtime_core()

            self.add(
                "Runtime Core",
                "OK",
                "created successfully",
            )

            report = core.inspector.health()

            for name, status in report.items():

                self.add(
                    f"Runtime {name}",
                    "OK" if status == "healthy" else "WARN",
                    status,
                )

        except Exception as exc:

            self.add(
                "Runtime Core",
                "FAIL",
                str(exc),
            )                
    
    def check_runtime_package(self):

        required = [

            "buster/runtime/core.py",

            "buster/runtime/dispatcher.py",

            "buster/runtime/state_store.py",

            "buster/runtime/inspector.py",

            "buster/runtime/sdk_bootstrap.py",

            "buster/runtime/job_manager.py",

        ]

        for rel in required:

            path = ROOT / rel

            self.add(

                f"Runtime: {Path(rel).name}",

                "OK" if path.exists() else "FAIL",

                "found" if path.exists() else "missing",

            )
            
            
    def check_runtime_panels(self):

        required = [

            "buster/ui/v9/panels/runtime_panel/runtime_timeline_panel.py",

            "buster/ui/v9/panels/runtime_panel/overview_panel.py",

            "buster/ui/v9/panels/runtime_panel/timeline_panel.py",

            "buster/ui/v9/panels/runtime_panel/console_panel.py",

            "buster/ui/v9/panels/runtime_panel/live_panel.py",

        ]

        for rel in required:

            path = ROOT / rel

            self.add(

                f"Runtime Panel: {Path(rel).stem}",

                "OK" if path.exists() else "FAIL",

                "found" if path.exists() else "missing",
 
            )        
    
    def check_runtime_compile(self):

        runtime = ROOT / "buster/runtime"

        failures = []

        for file in runtime.rglob("*.py"):

            code, _, err = self.run_cmd(

                [

                    sys.executable,

                    "-m",

                    "py_compile",

                    str(file),

                ],

                timeout=20,

            )

            if code != 0:

                failures.append(file.name)

        if failures:

            self.add(

                "Runtime Compile",

                "FAIL",

                ", ".join(failures),

            )

        else:

            self.add(

                "Runtime Compile",

                "OK",

                "all runtime modules compile",

            )
    
    def check_runtime_inspector(self):

        try:

            from buster.runtime.inspector import RuntimeInspector

            self.add(

                "Runtime Inspector",

                "OK",

                "available",

            )

        except Exception as exc:

            self.add(

                "Runtime Inspector",

                "FAIL",

                str(exc),

            )
    
    def check_dispatcher(self):

        try:

            from buster.runtime.dispatcher import RuntimeDispatcher

            RuntimeDispatcher()

            self.add(

                "Dispatcher",

                "OK",

                "created",

            )

        except Exception as exc:

            self.add(

                "Dispatcher",

                "FAIL",

                str(exc),

            )
    
    

    def run_all(self):
        self.check_python()
        self.check_git()
        self.check_network()
        self.check_internet_dependencies()
        self.check_voice_dependencies()
        self.check_ollama()
        self.check_data_dirs()
        self.check_buster_files()
        self.check_import_core_modules()
        self.check_provider_diagnostics()
        self.check_runtime_package()

        self.check_runtime_compile()

        self.check_dispatcher()

        self.check_runtime_inspector()

        self.check_runtime()
        
        self.check_pytest()
        

    def print_report(self):
        print()
        print("==================================================")
        print("BUSTER DOCTOR REPORT")
        print("==================================================")

        width = max(len(r.name) for r in self.results) if self.results else 10
        for result in self.results:
            icon = "OK " if result.ok else ("WARN" if result.warn else "FAIL")
            print(f"{icon:<5} {result.name:<{width}}  {result.detail}")

        ok = sum(1 for r in self.results if r.ok)
        warn = sum(1 for r in self.results if r.warn)
        fail = sum(1 for r in self.results if r.fail)

        print("==================================================")
        print(f"SUMMARY: OK={ok} WARN={warn} FAIL={fail}")

        if fail:
            print("OVERALL: NEEDS ATTENTION")
        elif warn:
            print("OVERALL: READY WITH WARNINGS")
        else:
            print("OVERALL: READY FOR DEVELOPMENT")

        print("==================================================")

    def exit_code(self) -> int:
        return 1 if any(r.fail for r in self.results) else 0


def main():

    args = {arg.lower() for arg in sys.argv[1:]}

    auto_fix = "--fix" in args
    run_tests = "--no-tests" not in args

    doctor = BusterDoctor(
        auto_fix=auto_fix,
        run_tests=run_tests,
    )

    if "runtime" in args:

        doctor.check_python()
        doctor.check_runtime_package()
        doctor.check_runtime_compile()
        doctor.check_dispatcher()
        doctor.check_runtime_inspector()
        doctor.check_runtime()
        doctor.check_runtime_panels()

    elif "ui" in args:

        doctor.check_python()
        doctor.check_runtime_panels()

    elif "imports" in args:

        doctor.check_import_core_modules()

    else:

        doctor.run_all()

    doctor.print_report()

    raise SystemExit(
        doctor.exit_code()
    )


if __name__ == "__main__":
    main()
