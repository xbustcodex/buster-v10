import sys
from PySide6.QtWidgets import QApplication
from buster.ui.v9.v9_shell import V9MainWindow, FaceWindow

app = QApplication(sys.argv)

main = V9MainWindow()
face = FaceWindow()

main.show()
face.show()

sys.exit(app.exec())
