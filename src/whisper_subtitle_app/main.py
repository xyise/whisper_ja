from __future__ import annotations

import sys

from PySide6 import QtWidgets

from .app_controller import AppController


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    controller = AppController()
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
