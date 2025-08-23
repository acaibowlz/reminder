LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[%(levelname)s] %(name)s: %(message)s"},
        "uvicorn": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
    },
    "handlers": {
        "stream": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
        "uvicorn": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["stream"],
        "level": "INFO",
    },
    "loggers": {
        "uvicorn.error": {
            "handlers": ["uvicorn"],
            "level": "INFO",
            "propagate": False,
        },
        # Disable uvicorn.access logs
        "uvicorn.access": {
            "handlers": [],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}
