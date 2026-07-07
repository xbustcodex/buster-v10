import sys
from PySide6.QtWidgets import QApplication
from buster.ui.v12.mission_control import MissionControlV12

def main():
    app = QApplication(sys.argv)
    window = MissionControlV12()
    window.resize(1600, 950)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
