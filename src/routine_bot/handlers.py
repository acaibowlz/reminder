import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg
import requests
from dateutil.relativedelta import relativedelta
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent, UnfollowEvent
from linebot.v3.webhooks.models.sticker_message_content import re

from routine_bot.constants import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    SUPPORTED_COMMANDS,
    SUPPORTED_UNITS,
    ChatType,
    Command,
    CycleUnit,
    NewEventSteps,
)
from routine_bot.db import (
    add_chat,
    add_event,
    add_user,
    conn,
    get_event_id,
    get_ongoing_chat,
    update_chat,
)
from routine_bot.messages import ErrorMsg, NewEventMsg
from routine_bot.models import ChatData, EventData

logger = logging.getLogger(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


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


def handle_new_event_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> str:
    if chat.current_step == NewEventSteps.INPUT_NAME:
        logger.info("Processing event name input")
        event_name = msg.strip()
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
        logger.info(f"Added event name {event_name} to chat payload")
        return NewEventMsg(chat.payload).prompt_for_start_date()

    elif chat.current_step == NewEventSteps.INPUT_START_DATE:
        logger.info("Processing start date input")
        start_date = parse_date(msg)
        if start_date is None:
            logger.info(f"Invalid start date input: {msg}")
            return ErrorMsg.invalid_start_date_input()
        chat.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
        chat.current_step = NewEventSteps.INPUT_REMINDER
        logger.info(f"Added start date {chat.payload['start_date'][:10]} to chat payload")
        update_chat(chat, conn)
        return NewEventMsg(chat.payload).prompt_for_reminder()

    elif chat.current_step == NewEventSteps.INPUT_REMINDER:
        logger.info("Processing reminder input")
        if msg.upper() == "Y":
            chat.payload["reminder"] = True
            chat.current_step = NewEventSteps.INPUT_REMINDER_CYCLE
            logger.info("Added reminder=True to chat payload")
            update_chat(chat, conn)
            return NewEventMsg(chat.payload).prompt_for_reminder_cycle()
        elif msg.upper() == "N":
            chat.payload["reminder"] = False
            chat.current_step = None
            chat.is_completed = True
            logger.info("Added reminder=False to chat payload")
            update_chat(chat, conn)
            logger.info(f"Chat completed: {chat.chat_id}")

            event_data = EventData(
                event_id=str(uuid.uuid4()),
                event_name=chat.payload["event_name"],
                user_id=chat.user_id,
                last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
                reminder=False,
            )
            add_event(event_data, conn)
            return NewEventMsg(chat.payload).completion_no_reminder()
        else:
            logger.info(f"Invalid reminder input: {msg}")
            return ErrorMsg.invalid_reminder_input()

    elif chat.current_step == NewEventSteps.INPUT_REMINDER_CYCLE:
        logger.info("Processing reminder cycle input")
        if parse_reminder_cycle(msg) is None:
            logger.info(f"Invalid reminder cycle input: {msg}")
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
        chat.is_completed = True
        logger.info(f"Added reminder cycle {chat.payload['reminder_cycle']} to chat payload")
        logger.info(f"Next reminder: {next_reminder.strftime('%Y-%m-%d')}")
        update_chat(chat, conn)
        logger.info(f"Chat completed: {chat.chat_id}")

        event_data = EventData(
            event_id=str(uuid.uuid4()),
            event_name=chat.payload["event_name"],
            user_id=chat.user_id,
            last_done_at=datetime.fromisoformat(chat.payload["start_date"]),
            reminder=True,
            reminder_cycle=chat.payload["reminder_cycle"],
            next_reminder=next_reminder,
        )
        add_event(event_data, conn)
        return NewEventMsg(chat.payload).completion_with_reminder()


def handle_ongoing_chat(msg: str, chat: ChatData, conn: psycopg.Connection) -> str:
    if chat.chat_type == ChatType.NEW_EVENT:
        return handle_new_event_chat(msg, chat, conn)


def get_reply_message(msg: str, user_id: str) -> str:
    logger.debug(f"Message received: {msg}")
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        # handle ongoing chat if there exists
        chat = get_ongoing_chat(user_id, conn)
        if chat is not None:
            logger.debug(f"Ongoing chat found: {chat.chat_id}")
            logger.debug(f"Chat type: {chat.chat_type}")
            logger.debug(f"Current step: {chat.current_step}")
            return handle_ongoing_chat(msg, chat, conn)

        # validate if msg is command
        if not msg.startswith("/"):
            return "hello!"
        if msg not in SUPPORTED_COMMANDS:
            return ErrorMsg.unrecognized_command()

        # create new chat
        chat_id = str(uuid.uuid4())
        if msg == Command.NEW:
            logger.info("Creating new chat, chat type: new event")
            chat = ChatData(
                chat_id=chat_id, user_id=user_id, chat_type=ChatType.NEW_EVENT, current_step=NewEventSteps.INPUT_NAME
            )
            add_chat(chat, conn)
            return NewEventMsg().prompt_for_event_name()


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    reply_message = get_reply_message(msg=event.message.text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
