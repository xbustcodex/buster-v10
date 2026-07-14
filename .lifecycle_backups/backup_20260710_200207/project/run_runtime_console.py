import sys
from PySide6.QtWidgets import QApplication

from buster.ui.v11.runtime_console import RuntimeConsole


def main():
    app = QApplication(sys.argv)
    window = RuntimeConsole()
    window.resize(1600, 950)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
