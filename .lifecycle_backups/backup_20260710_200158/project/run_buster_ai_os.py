import sys
from PySide6.QtWidgets import QApplication
from buster.ui.os1.main_window import BusterAIOSMainWindow

def main():
    app = QApplication(sys.argv)
    window = BusterAIOSMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
