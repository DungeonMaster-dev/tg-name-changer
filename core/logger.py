import logging
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")


def setup_logger(ui_callback=None) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("tg_name_changer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S")

    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    if ui_callback is not None:
        class UiHandler(logging.Handler):
            def emit(self, record):
                try:
                    ui_callback(self.format(record))
                except Exception:
                    pass

        ui_handler = UiHandler()
        ui_handler.setFormatter(fmt)
        logger.addHandler(ui_handler)

    return logger