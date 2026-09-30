import logging


class Logger:
    """Centraliza o registro de erros da aplicação."""

    @staticmethod
    def configurar():
        logging.basicConfig(
            filename="error.log",
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S",
        )

    @staticmethod
    def registrar(error: Exception):
        logging.error(str(error), exc_info=True)
