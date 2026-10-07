import logging
from pathlib import Path


class Logger:
    """Centraliza o registro de erros da aplicacao."""

    @staticmethod
    def configurar():
        log_file = Path(__file__).resolve().parent / "error.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S",
        )

    @staticmethod
    def registrar(error: Exception):
        logging.error(str(error), exc_info=True)
