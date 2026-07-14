from pathlib import Path
from datetime import datetime

class Logger:
    def __init__(self, log_dir):
        self.file = Path(log_dir) / "buster.log"
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def info(self, msg: str):
        self.write("INFO", msg)

    def error(self, msg: str):
        self.write("ERROR", msg)

    def write(self, level: str, msg: str):
        self.file.open("a", encoding="utf-8").write(
            f"{datetime.now().isoformat(timespec='seconds')} [{level}] {msg}\n"
        )
