import logging
import os

from dotenv import load_dotenv


def getenv(env: str):
    if (res := os.getenv(env)) is None:
        raise EnvironmentError(f"Environment variable {env} is not set")
    return res


load_dotenv()


BOT_TOKEN = getenv("BOT_TOKEN")
UPDATE_EACH_MINUTES = 5

LOGGING_LEVEL = logging.INFO
LOGGING_FILE = "logs/app.log"
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        },
    },
    "handlers": {
        "stream_handler": {
            "level": LOGGING_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file_handler": {
            "level": LOGGING_LEVEL,
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_FILE,
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {
            "handlers": ["stream_handler", "file_handler"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
    },
}
