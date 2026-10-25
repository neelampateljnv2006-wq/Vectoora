import sys; from PyQt6.QtWidgets import QApplication; import main; app = QApplication(sys.argv); window = main.VectooraApp(); window.showMaximized(); sys.exit(app.exec())
