import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QLabel


def main():

    app = QApplication(sys.argv)

    label = QLabel(
        "RoboCutter V1.1"
    )

    label.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()