from pathlib import Path

p = Path("buster/core/runtime.py")
text = p.read_text(encoding="utf-8")

# Add v9 imports
if "from buster.ui.v9.v9_shell import V9MainWindow, FaceWindow" not in text:
    text = text.replace(
        "from buster.ui.main_window import MainWindow\n",
        "from buster.ui.main_window import MainWindow\nfrom buster.ui.v9.v9_shell import V9MainWindow, FaceWindow\n",
    )

old = '''    def run(self):
        app = QApplication(sys.argv)
        app.setApplicationName(self.settings.app_name)
        window = MainWindow(self.settings, self.state, self.services, self.bus)
        window.show()
        sys.exit(app.exec())
'''

new = '''    def run(self):
        app = QApplication(sys.argv)
        app.setApplicationName(self.settings.app_name)

        USE_V9_UI = True

        if USE_V9_UI:
            window = V9MainWindow(
                services=self.services,
                settings=self.settings,
            )
            face = FaceWindow()
            face.show()
        else:
            window = MainWindow(self.settings, self.state, self.services, self.bus)

        window.show()
        sys.exit(app.exec())
'''

if old not in text:
    raise SystemExit("Could not find runtime run() block. Patch manually.")

text = text.replace(old, new)
p.write_text(text, encoding="utf-8")

print("Runtime now launches v9 UI by default.")