import os

from dotenv import load_dotenv

# ------------------------------ Env. Variables ------------------------------ #

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")

# ---------------------------------- Config ---------------------------------- #

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[%(levelname)s] %(name)s - %(message)s"}},
    "handlers": {
        "stream": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "handlers": ["stream"],
        "level": "INFO",
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


TODAY = "今天"
TOMORROW = "明天"
YESTERDAY = "昨天"


class Command:
    NEW = "/new"
    FIND = "/find"
    UPDATE = "/update"
    EDIT = "/edit"
    DELETE = "/delete"
    VIEW = "/view"
    # premium features
    UPGRADE = "/upgrade"
    SHARE = "/share"
    DOWNGRADE = "/downgrade"


SUPPORTED_COMMANDS = {v for k, v in vars(Command).items() if k.isupper()}


class CycleUnit:
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


SUPPORTED_UNITS = {v for k, v in vars(CycleUnit).items() if k.isupper()}

# ------------------------------- Event States ------------------------------- #


class ChatType:
    NEW_EVENT = "new_event"
    FIND_EVENT = "find_event"
    UPDATE_EVENT = "update_event"
    EDIT_EVENT = "edit_event"
    DELETE_EVENT = "delete_event"


class NewEventState:
    INPUT_NAME = "input_name"
    INPUT_START_DATE = "input_start_date"
    INPUT_REMINDER = "input_reminder"
    INPUT_CYCLE_PERIOD = "input_cycle_period"
    COMPLETE = "complete"
