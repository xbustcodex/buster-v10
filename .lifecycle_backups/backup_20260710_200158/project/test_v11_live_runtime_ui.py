import sys
from PySide6.QtWidgets import QApplication

from buster.ui.v11.live_runtime_ui import BusterLiveRuntimeUI


def main():
    app = QApplication(sys.argv)
    window = BusterLiveRuntimeUI()
    window.resize(1500, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
