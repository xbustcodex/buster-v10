import sys
from PySide6.QtWidgets import QApplication

from buster.ui.v10.runtime_dashboard import MissionControlRuntimeDashboard


def main():
    app = QApplication(sys.argv)
    window = MissionControlRuntimeDashboard()
    window.resize(1400, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
