"""Qt shutdown guard: never destroy a parent while its native threads run."""

from PyQt6 import sip
from PyQt6.QtCore import QThread, QTimer


def defer_close_for_workers(window, event):
    running = [w for w in window.findChildren(QThread)
               if not sip.isdeleted(w) and w.isRunning()]
    if not running:
        return False
    window._closing = True
    event.ignore()
    window.setEnabled(False)
    for worker in running:
        worker.requestInterruption()
        try:
            worker.disconnect()
        except (TypeError, RuntimeError):
            pass
        if hasattr(worker, "provide_error_decision"):
            worker.provide_error_decision("stop")
    QTimer.singleShot(100, window.close)
    return True
