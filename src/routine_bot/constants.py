import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# ------------------------------ Env. Variables ------------------------------ #

load_dotenv()

ENV = os.getenv("ENV")

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")
REMINDER_TOKEN = os.getenv("REMINDER_TOKEN")

TZ_TAIPEI = ZoneInfo("Asia/Taipei")
FREE_PLAN_MAX_EVENTS = 5

# ---------------------------------- Config ---------------------------------- #

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[%(levelname)8s] %(name)-20s - %(message)s"}},
    "handlers": {
        "stream": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "handlers": ["stream"],
        "level": "DEBUG" if ENV == "develop" else "INFO",
    },
    "loggers": {
        "uvicorn.error": {
            "handlers": ["stream"],
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
