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

from routine_bot.constants import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    SUPPORTED_COMMANDS,
    SUPPORTED_UNITS,
    ChatType,
    Command,
    CycleUnit,
    NewEventState,
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


def parse_cycle_period(msg: str) -> tuple[int, str] | None:
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


def handle_new_event_chat(msg: str, chat_data: ChatData, conn: psycopg.Connection) -> str:
    if chat_data.current_step == NewEventState.INPUT_NAME:
        event_name = msg
        # validate event name
        if len(event_name) > 20:
            return ErrorMsg.event_name_too_long()
        if get_event_id(chat_data.user_id, event_name, conn) is not None:
            return ErrorMsg.event_name_duplicated(event_name)
        # store event name in state data
        chat_data.payload["event_name"] = event_name
        chat_data.current_step = NewEventState.INPUT_START_DATE
        update_chat(chat_data, conn)
        return NewEventMsg(chat_data.payload).prompt_for_start_date()

    elif chat_data.current_step == NewEventState.INPUT_START_DATE:
        start_date = parse_date(msg)
        if start_date is None:
            return ErrorMsg.unrecognized_date()
        chat_data.payload["start_date"] = start_date.isoformat()  # datetime is not JSON serializable
        chat_data.current_step = NewEventState.INPUT_REMINDER
        update_chat(chat_data, conn)
        return NewEventMsg(chat_data.payload).prompt_for_reminder()

    elif chat_data.current_step == NewEventState.INPUT_REMINDER:
        if msg.upper() == "Y":
            chat_data.payload["reminder"] = True
            chat_data.current_step = NewEventState.INPUT_CYCLE_PERIOD
            update_chat(chat_data, conn)
            return NewEventMsg(chat_data.payload).prompt_for_cycle_period()
        elif msg.upper() == "N":
            chat_data.payload["reminder"] = False
            chat_data.current_step = None
            chat_data.is_completed = True
            update_chat(chat_data, conn)

            event_data = EventData(
                event_id=str(uuid.uuid4()),
                event_name=chat_data.payload["event_name"],
                user_id=chat_data.user_id,
                last_done_at=datetime.fromisoformat(chat_data.payload["start_date"]),
                reminder=False,
            )
            add_event(event_data, conn)
            return NewEventMsg(chat_data.payload).completion_no_reminder()
        else:
            return ErrorMsg.unrecognized_reminder_input()

    elif chat_data.current_step == NewEventState.INPUT_CYCLE_PERIOD:
        if parse_cycle_period(msg) is None:
            return ErrorMsg.unrecognized_cycle_period()
        chat_data.payload["cycle_period"] = msg
        increment, unit = parse_cycle_period(msg)
        start_date = datetime.fromisoformat(chat_data.payload["start_date"])

        if unit == CycleUnit.DAY:
            offset = relativedelta(days=+increment)
        elif unit == CycleUnit.WEEK:
            offset = relativedelta(weeks=+increment)
        elif unit == CycleUnit.MONTH:
            offset = relativedelta(months=+increment)
        cycle_ends_at = start_date + offset
        chat_data.current_step = None
        chat_data.is_completed = True
        update_chat(chat_data, conn)

        event_data = EventData(
            event_id=str(uuid.uuid4()),
            event_name=chat_data.payload["event_name"],
            user_id=chat_data.user_id,
            last_done_at=datetime.fromisoformat(chat_data.payload["start_date"]),
            reminder=True,
            cycle_period=chat_data.payload["cycle_period"],
            cycle_ends_at=cycle_ends_at,
        )
        add_event(event_data, conn)
        return NewEventMsg(chat_data.payload).completion_with_reminder()


def handle_ongoing_chat(msg: str, chat_data: ChatData, conn: psycopg.Connection) -> str:
    if chat_data.chat_type == ChatType.NEW_EVENT:
        return handle_new_event_chat(msg, chat_data, conn)


def get_reply_message(msg: str, user_id: str) -> str:
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        # handle ongoing chat if there exists
        chat = get_ongoing_chat(user_id, conn)
        if chat is not None:
            return handle_ongoing_chat(msg, chat, conn)

        # validate if msg is command
        if not msg.startswith("/"):
            return "hello!"
        if msg not in SUPPORTED_COMMANDS:
            return ErrorMsg.unrecognized_command()

        # create new chat
        chat_id = str(uuid.uuid4())
        if msg == Command.NEW:
            chat_data = ChatData(
                chat_id=chat_id, user_id=user_id, chat_type=ChatType.NEW_EVENT, current_step=NewEventState.INPUT_NAME
            )
            add_chat(chat_data, conn)
            return NewEventMsg().prompt_for_event_name()


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    reply_message = get_reply_message(msg=event.message.text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
