import os

from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")

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
    # premium feature
    UPGRADE = "/upgrade"
    SHARE = "/share"
    DOWNGRADE = "/downgrade"
    SUPPORTED_COMMANDS = {NEW, FIND, UPDATE, EDIT, DELETE, VIEW}


class CycleUnit:
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    SUPPORTED_UNITS = {DAY, WEEK, MONTH}


class ChatType:
    NEW_EVENT = "new_event"
    FIND_EVENT = "find_event"
    UPDATE_EVENT = "update_event"
    EDIT_EVENT = "edit_event"
    DELETE_EVENT = "delete_event"


class NewEventState:
    NAME_ENTERED = 0
    START_DATE_ENTERED = 1
    REMINDER_ENTERED = 2


class UpdateEventState:
    NAME_ENTERED = 0


class EditEventState:
    NAME_ENTERED = 0
    FIELD_TO_EDIT_ENTERED = 1
    REMINDER_ENTERED = 2


class DeleteEventState:
    NAME_ENTERED = 0
