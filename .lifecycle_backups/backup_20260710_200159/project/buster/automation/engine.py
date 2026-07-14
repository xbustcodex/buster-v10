from pathlib import Path

class AutomationEngine:
    def __init__(self, screenshots_dir):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def move_mouse_from_text(self, text):
        try:
            x, y = [int(p) for p in text.replace(",", " ").split()[:2]]
            return self.move_mouse(x, y)
        except Exception:
            return "Use: move mouse 100 100"

    def move_mouse(self, x, y):
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=0.2)
            return f"Moved mouse to {x}, {y}."
        except Exception as exc:
            return f"Mouse move failed: {exc}"

    def click(self):
        try:
            import pyautogui
            pyautogui.click()
            return "Clicked."
        except Exception as exc:
            return f"Click failed: {exc}"

    def type_text(self, text):
        try:
            import pyautogui
            pyautogui.write(text, interval=0.01)
            return "Typed text."
        except Exception as exc:
            return f"Typing failed: {exc}"
