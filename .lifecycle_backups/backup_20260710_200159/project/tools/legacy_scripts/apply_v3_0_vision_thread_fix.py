
from pathlib import Path
import shutil
import re

ROOT = Path.cwd()

def backup(path: Path):
    if path.exists():
        b = path.with_suffix(path.suffix + ".bak_vision_thread_fix")
        if not b.exists():
            shutil.copy2(path, b)

def read(path):
    return path.read_text(encoding="utf-8")

def write(path, text):
    path.write_text(text, encoding="utf-8")

def find_method_block(text, method_name):
    pattern = rf"^    def {method_name}\(.*?\):\n"
    m = re.search(pattern, text, flags=re.M)
    if not m:
        return None, None
    start = m.start()
    next_m = re.search(r"^    def \w+\(.*?\):\n", text[m.end():], flags=re.M)
    if not next_m:
        return start, len(text)
    return start, m.end() + next_m.start()

def patch_main_window():
    path = ROOT / "buster/ui/main_window.py"
    if not path.exists():
        print("Could not find buster/ui/main_window.py")
        return

    backup(path)
    s = read(path)

    new_run_command = '''    def run_command(self, text):
        self.chat.append(f"You: {text}")
        self.set_mode("thinking")

        # Qt objects like QTimer, camera windows, and QWidget updates must run on
        # the main UI thread. Vision start/stop is therefore handled synchronously.
        main_thread_commands = {
            "start vision", "show vision", "open vision", "start camera",
            "show camera", "open camera", "stop vision", "hide vision",
            "stop camera",
        }

        if text.strip().lower() in main_thread_commands:
            try:
                reply = self.services.get("brain").process(text)
            except Exception as exc:
                reply = f"Command failed: {exc}"
            self.handle_brain_result(text, reply)
            return

        def worker():
            try:
                reply = self.services.get("brain").process(text)
            except Exception as exc:
                reply = f"Command failed: {exc}"
            self.bridge.brain_result.emit(text, reply)

        self.services.get("thread_pool").submit(worker)

'''

    start, end = find_method_block(s, "run_command")
    if start is None:
        print("Could not find run_command")
        return

    s = s[:start] + new_run_command + s[end:]
    write(path, s)
    print("patched main_window.py")

def main():
    print("Applying Buster v3.0 Vision Thread Fix...")
    patch_main_window()
    print("Done. Now run: python main.py")
    print("Test:")
    print("  start vision")
    print("  wait 2 seconds")
    print("  vision status")
    print("  detect objects")
    print("  detect faces")

if __name__ == "__main__":
    main()
