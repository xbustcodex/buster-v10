import os
import subprocess

class WindowsSystemAccess:
    def env_summary(self):
        keys = ["USERNAME", "USERPROFILE", "COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE"]
        return "\n".join(f"{k}: {os.environ.get(k, '')}" for k in keys)

    def where_python(self):
        try:
            result = subprocess.run(["where", "python"], capture_output=True, text=True, shell=True)
            return result.stdout.strip() or result.stderr.strip()
        except Exception as exc:
            return str(exc)

    def running_processes(self):
        try:
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                shell=True
            )
            return "\n".join(result.stdout.splitlines()[:40])
        except Exception as exc:
            return str(exc)
