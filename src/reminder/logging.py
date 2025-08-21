import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "stream": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "handlers": ["stream"],
        "level": "INFO",
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
