import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg
import requests
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent, UnfollowEvent

from routine_bot.const import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    SUPPORTED_COMMANDS,
    TODAY,
    TOMORROW,
    YESTERDAY,
    ChatType,
    Command,
    NewEventState,
)
from routine_bot.db import (
    add_chat,
    add_user,
    conn,
    get_ongoing_chat_data,
    update_chat,
)
from routine_bot.messages import NewEventMsg
from routine_bot.models import ChatData

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


def parse_starting_date(text: str) -> datetime | None:
    taipei_timezone = ZoneInfo("Asia/Taipei")
    if len(text) == 2:
        datetime_mapping = {
            TODAY: datetime.now(taipei_timezone),
            TOMORROW: datetime.now(taipei_timezone) + timedelta(days=1),
            YESTERDAY: datetime.now(taipei_timezone) - timedelta(days=1),
        }
        if text not in datetime_mapping:
            return None
        starting_date = datetime_mapping[text]
    elif len(text) == 4:
        try:
            starting_date = datetime.strptime(text, "%m%d")
            starting_date = starting_date.replace(year=datetime.now().year, tzinfo=taipei_timezone)
        except ValueError:
            return None
    elif len(text) == 8:
        try:
            starting_date = datetime.strptime(text, "%Y%m%d")
            starting_date = starting_date.replace(tzinfo=taipei_timezone)
        except ValueError:
            return None
    else:
        return None


def handle_new_event_chat(msg: str, chat_data: ChatData, conn: psycopg.Connection) -> str:
    if chat_data.next_step == NewEventState.ENTER_NAME:
        event_name = msg
        chat_data.state_data["event_name"] = event_name
        update_chat(chat_data, conn)
        return NewEventMsg(event_name).prompt_for_starting_date


def handle_ongoing_chat(msg: str, data: ChatData, conn: psycopg.Connection) -> str:
    if data.chat_type == ChatType.NEW_EVENT:
        return handle_new_event_chat(msg, data, conn)


def get_reply_message(msg: str, user_id: str) -> str:
    # first process with the on-going chat
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat_data = get_ongoing_chat_data(user_id, conn)
        if chat_data is not None:
            return handle_ongoing_chat(msg, chat_data, conn)

        if not msg.startswith("/"):
            return "hello!"
        if msg not in SUPPORTED_COMMANDS:
            return "Unknown command!"

        if msg == Command.NEW:
            new_chat = ChatData(
                chat_id=str(uuid.uuid4()),
                user_id=user_id,
                chat_type=ChatType.NEW_EVENT,
                current_step=NewEventState.START,
                next_step=NewEventState.ENTER_NAME,
            )
            add_chat(new_chat, conn)
            return "請輸入新事件的名稱"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    reply_message = get_reply_message(msg=event.message.text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
