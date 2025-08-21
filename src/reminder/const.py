import os

from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")


class Command:
    NEW = "/new"
    UPDATE = "/update"
    EDIT = "/edit"
    DELETE = "/delete"
    VIEW = "/view"
    UPGRADE = "/upgrade"
    SHARE = "/share"
    DOWNGRADE = "/downgrade"
