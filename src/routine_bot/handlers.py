import logging
import re
import unicodedata
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg
import requests
from dateutil.relativedelta import relativedelta
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent, UnfollowEvent

from routine_bot.constants import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
)
from routine_bot.db import (
    add_chat,
    add_event,
    add_update,
    add_user,
    conn,
    get_chat,
    get_event,
    get_event_id,
    get_event_recent_update_times,
    get_ongoing_chat_id,
    update_chat,
)
from routine_bot.enums import (
    SUPPORTED_COMMANDS,
    SUPPORTED_UNITS,
    ChatStatus,
    ChatType,
    Command,
    CycleUnit,
    FindEventSteps,
    NewEventSteps,
)
from routine_bot.messages import AbortMsg, ErrorMsg, FindEventMsg, NewEventMsg
from routine_bot.models import ChatData, EventData, UpdateData

logger = logging.getLogger(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ------------------------------ Util Functions ------------------------------ #


def sanitize_msg(msg: str) -> str:
    """
    Cleans and normalizes user input text for consistent downstream processing.

    Steps:
    1. Trim leading/trailing whitespace and newlines
    2. Normalize Unicode (NFKC) — converts fullwidth to halfwidth, etc.
    3. Collapse multiple spaces/newlines
    4. Remove invisible control characters
    """
    if not msg:
        return ""
    text = unicodedata.normalize("NFKC", msg)
    text = text.strip()
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    return text


def validate_event_name(event_name: str) -> str | None:
    """
    Return None if the event name is valid, or the error msg will be returned.
    """
    if len(event_name) < 2:
        return "事件名稱不可以少於 2 字元🤣\n請再試一次😌"
    if len(event_name) > 20:
        return "事件名稱不可以超過 20 字元🤣\n請再試一次😌"
    invalid_chars = re.findall(r"[^\u4e00-\u9fffA-Za-z0-9 _-]", event_name)
    if invalid_chars:
        invalid_chars = list(dict.fromkeys(invalid_chars))
        wrapped = "、".join([f"「{ch}」" for ch in invalid_chars])
        return f"無效的字元：{wrapped}\n請再試一次😌"
    return None


def parse_date(msg: str) -> datetime | None:
    taipei = ZoneInfo("Asia/Taipei")
    if len(msg) == 2:
        datetime_mapping = {
            "今天": datetime.now(),
            "明天": datetime.now() + timedelta(days=1),
            "昨天": datetime.now() - timedelta(days=1),
        }
        if msg not in datetime_mapping:
            return None
        date = datetime_mapping[msg]
        date = date.replace(tzinfo=taipei, hour=0, minute=0, second=0, microsecond=0)
    elif len(msg) == 4:
        try:
            msg = f"{datetime.now().year}{msg}"
            date = datetime.strptime(msg, "%Y%m%d")
            date = date.replace(tzinfo=taipei)
        except ValueError:
            return None
    elif len(msg) == 8:
        try:
            date = datetime.strptime(msg, "%Y%m%d")
            date = date.replace(tzinfo=taipei)
        except ValueError:
            return None
    else:
        return None
    return date


def parse_reminder_cycle(msg: str) -> tuple[int, str] | None:
    try:
        value, unit = msg.split(" ", maxsplit=1)
    except ValueError:
        return None
    try:
        value = int(value)
    except ValueError:
        return None
    if unit not in SUPPORTED_UNITS:
        return None
    return value, unit


# ------------------------------ Chat Handlers ------------------------------- #


def handle_new_event_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> str:
    if chat.current_step == NewEventSteps.INPUT_NAME:
        logger.info("Processing event name input")
        event_name = msg
        # validate event name
        error_msg = validate_event_name(event_name)
        if error_msg is not None:
            logger.info(f"Invalid event name input: {event_name}")
            return error_msg
        if get_event_id(chat.user_id, event_name, conn) is not None:
            return ErrorMsg.event_name_duplicated(event_name)
        # store event name in state data
        chat.payload["event_name"] = event_name
        chat.current_step = NewEventSteps.INPUT_START_DATE
        update_chat(chat, conn)
        logger.info(f"Added to chat payload: event_name='{event_name}'")
        return NewEventMsg.prompt_for_start_date(chat.payload)

    elif chat.current_step == NewEventSteps.INPUT_START_DATE:
        logger.info("Processing start date input")
        start_date = parse_date(msg)
        if start_date is None:
            logger.info(f"Invalid start date input: {msg}")
            return ErrorMsg.invalid_start_date_input()
        chat.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
        chat.current_step = NewEventSteps.INPUT_REMINDER
        logger.info(f"Added to chat payload: start_date='{chat.payload['start_date']}'")
        update_chat(chat, conn)
        return NewEventMsg.prompt_for_reminder(chat.payload)

    elif chat.current_step == NewEventSteps.INPUT_REMINDER:
        logger.info("Processing reminder input")
        if msg.upper() == "Y":
            chat.payload["reminder"] = True
            chat.current_step = NewEventSteps.INPUT_REMINDER_CYCLE
            logger.info("Added to chat payload: reminder=True")
            update_chat(chat, conn)
            return NewEventMsg.prompt_for_reminder_cycle(chat.payload)
        elif msg.upper() == "N":
            chat.payload["reminder"] = False
            chat.current_step = None
            chat.status = ChatStatus.COMPLETED.value
            logger.info("Added to chat payload: reminder=False")
            update_chat(chat, conn)
            logger.info(f"Chat completed: {chat.chat_id}")

            event_id = str(uuid.uuid4())
            event = EventData(
                event_id=event_id,
                event_name=chat.payload["event_name"],
                user_id=chat.user_id,
                last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
                reminder=False,
            )
            add_event(event, conn)
            update = UpdateData(
                update_id=str(uuid.uuid4()),
                event_id=event_id,
                event_name=chat.payload["event_name"],
                user_id=chat.user_id,
                done_at=datetime.fromisoformat(chat.payload["start_date"]),
            )
            add_update(update, conn)
            return NewEventMsg.event_created_no_reminder(chat.payload)
        else:
            logger.debug(f"Invalid reminder input: {msg}")
            return ErrorMsg.invalid_reminder_input()

    elif chat.current_step == NewEventSteps.INPUT_REMINDER_CYCLE:
        logger.info("Processing reminder cycle input")
        if parse_reminder_cycle(msg) is None:
            logger.debug(f"Invalid reminder cycle input: {msg}")
            return ErrorMsg.invalid_reminder_cycle()
        chat.payload["reminder_cycle"] = msg
        increment, unit = parse_reminder_cycle(msg)
        start_date = datetime.fromisoformat(chat.payload["start_date"])

        if unit == CycleUnit.DAY:
            offset = relativedelta(days=+increment)
        elif unit == CycleUnit.WEEK:
            offset = relativedelta(weeks=+increment)
        elif unit == CycleUnit.MONTH:
            offset = relativedelta(months=+increment)
        next_reminder = start_date + offset
        chat.current_step = None
        chat.status = ChatStatus.COMPLETED.value
        logger.info(f"Added to chat payload: reminder_cycle='{chat.payload['reminder_cycle']}'")
        logger.info(f"Next reminder: {next_reminder.strftime('%Y-%m-%d')}")
        update_chat(chat, conn)
        logger.info(f"Chat completed: {chat.chat_id}")

        event_id = str(uuid.uuid4())
        event = EventData(
            event_id=event_id,
            event_name=chat.payload["event_name"],
            user_id=chat.user_id,
            last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
            reminder=True,
            reminder_cycle=chat.payload["reminder_cycle"],
            next_reminder=next_reminder,
        )
        add_event(event, conn)
        update = UpdateData(
            update_id=str(uuid.uuid4()),
            event_id=event_id,
            event_name=chat.payload["event_name"],
            user_id=chat.user_id,
            done_at=datetime.fromisoformat(chat.payload["start_date"]),
        )
        add_update(update, conn)
        return NewEventMsg.event_created_with_reminder(chat.payload)


def handle_find_event_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> str:
    if chat.current_step == FindEventSteps.INPUT_NAME:
        logger.info("Processing event name input")
        event_name = msg

        error_msg = validate_event_name(event_name)
        if error_msg is not None:
            logger.info(f"Invalid event name input: {event_name}")
            return error_msg
        event_id = get_event_id(chat.user_id, event_name, conn)
        if event_id is None:
            logger.info(f"Event name not found: {event_name}")
            return ErrorMsg.event_name_not_found(event_name)

        logger.info(f"Event name input: {event_name}")
        logger.info(f"Event found: {event_id}")
        event = get_event(event_id, conn)
        recent_update_times = get_event_recent_update_times(event_id, conn)
        chat.current_step = None
        chat.status = ChatStatus.COMPLETED.value
        update_chat(chat, conn)
        logger.info(f"Chat completed: {chat.chat_id}")
        return FindEventMsg.format_event_summary(event, recent_update_times)


def create_new_chat(command: str, user_id: str, conn: psycopg.Connection) -> str:
    chat_id = str(uuid.uuid4())
    if command == Command.NEW:
        logger.info("Creating new chat, chat type: new event")
        chat = ChatData(
            chat_id=chat_id,
            user_id=user_id,
            chat_type=ChatType.NEW_EVENT,
            current_step=NewEventSteps.INPUT_NAME,
        )
        add_chat(chat, conn)
        return NewEventMsg().prompt_for_event_name()
    if command == Command.FIND:
        logger.info("Creating new chat, chat type: find event")
        chat = ChatData(
            chat_id=chat_id,
            user_id=user_id,
            chat_type=ChatType.FIND_EVENT,
            current_step=FindEventSteps.INPUT_NAME,
        )
        add_chat(chat, conn)
        return FindEventMsg.prompt_for_event_name()


def handle_ongoing_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> str:
    if chat.chat_type == ChatType.NEW_EVENT:
        return handle_new_event_chat(msg, chat, conn)
    if chat.chat_type == ChatType.FIND_EVENT:
        return handle_find_event_chat(msg, chat, conn)


def get_reply_message(msg: str, user_id: str) -> str:
    logger.debug(f"Message received: {msg}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        ongoing_chat_id = get_ongoing_chat_id(user_id, conn)

        if ongoing_chat_id is None:
            if msg == Command.ABORT:
                return AbortMsg.no_ongoing_chat()
            if not msg.startswith("/"):
                return "hello!"
            if msg not in SUPPORTED_COMMANDS:
                return ErrorMsg.unrecognized_command()
            return create_new_chat(msg, user_id, conn)

        chat = get_chat(ongoing_chat_id, conn)
        logger.debug(f"Ongoing chat found: {chat.chat_id}")
        logger.debug(f"Chat type: {chat.chat_type}")
        logger.debug(f"Current step: {chat.current_step}")

        if msg == Command.ABORT:
            chat.status = ChatStatus.ABORTED.value
            update_chat(chat, conn)
            logger.info(f"Chat aborted: {chat.chat_id}")
            return AbortMsg.ongoing_chat_aborted()

        return handle_ongoing_chat(msg, chat, conn)


# --------------------------- LINE Event Handlers ---------------------------- #


@handler.add(FollowEvent)
def handle_user_added(event: FollowEvent) -> None:
    user_id = event.source.user_id
    resp = requests.get(
        f"https://api.line.me/v2/bot/profile/{user_id}",
        headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
    )
    user_info = resp.json()
    display_name = user_info.get("displayName")
    picture_url = user_info.get("pictureUrl")
    logger.info(f"Added (or unblocked) by: {user_id}")
    logger.info(f"Display name: {display_name}")

    add_user(user_id=user_id, display_name=display_name, picture_url=picture_url, conn=conn)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="hello my new friend!")])
        )


@handler.add(UnfollowEvent)
def handle_user_blocked(event: UnfollowEvent) -> None:
    user_id = event.source.user_id
    logger.info(f"Blocked by: {user_id}")

    # handle if no user found
    pass


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    msg = sanitize_msg(event.message.text)
    reply_message = get_reply_message(msg=msg, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
