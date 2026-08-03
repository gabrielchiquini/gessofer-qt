from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from bridge.nfe import search_nfe_key

logger = logging.getLogger(__name__)


class NfeSearchWorker(QObject):
    """Worker object that runs the NFe SEFAZ search in a background thread.

    Signals:
        nfe_success(xml_path: str): Emitted when the search succeeds.
        nfe_error(message: str): Emitted when the search fails.
        nfe_finished(): Emitted after success or error (for cleanup).
    """

    nfe_success: Signal = Signal(str)
    nfe_error: Signal = Signal(str)

    def __init__(self, nfe_key: str, /) -> None:
        super().__init__()
        self._nfe_key = nfe_key

    @Slot(str)
    def start_search(self) -> None:
        """Start the NFe search in this worker thread.
        """
        try:
            xml_path: str = search_nfe_key(self._nfe_key)
            self.nfe_success.emit(xml_path)
        except Exception as exc:
            logger.error("Erro na busca NFe: %s", exc)
            logger.debug("Traceback", exc_info=True)
            self.nfe_error.emit(str(exc))
