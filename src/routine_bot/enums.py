from enum import StrEnum, auto

# ------------------------------ Command Enums ------------------------------- #


class Command(StrEnum):
    NEW = "/new"
    FIND = "/find"
    UPDATE = "/update"
    EDIT = "/edit"
    DELETE = "/delete"
    VIEW = "/view"
    ABORT = "/abort"
    # premium features
    UPGRADE = "/upgrade"
    SHARE = "/share"
    DOWNGRADE = "/downgrade"


SUPPORTED_COMMANDS = {command.value for command in Command}

# -------------------------------- Chat Enums -------------------------------- #


class ChatType(StrEnum):
    NEW_EVENT = auto()
    FIND_EVENT = auto()
    UPDATE_EVENT = auto()
    EDIT_EVENT = auto()
    DELETE_EVENT = auto()


class ChatStatus(StrEnum):
    ONGOING = auto()
    COMPLETED = auto()
    ABORTED = auto()


class CycleUnit(StrEnum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()


SUPPORTED_UNITS = {unit.value for unit in CycleUnit}


# ------------------------------- Event Steps -------------------------------- #


class NewEventSteps(StrEnum):
    INPUT_NAME = auto()
    INPUT_START_DATE = auto()
    INPUT_REMINDER = auto()
    INPUT_REMINDER_CYCLE = auto()


class FindEventSteps(StrEnum):
    INPUT_NAME = auto()
