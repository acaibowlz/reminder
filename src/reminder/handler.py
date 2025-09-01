import logging
import textwrap
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import requests
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent, UnfollowEvent

from reminder.const import (
    DATABASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    TODAY,
    TOMORROW,
    YESTERDAY,
    ChatType,
    Command,
    CycleUnit,
    NewEventState,
)
from reminder.db import (
    add_chat,
    add_event,
    add_user,
    conn,
    get_event_id,
    get_ongoing_chat_data,
    get_ongoing_chat_id,
    update_chat,
)
from reminder.message import DeleteEventMsg, EditEventMsg, ErrorMsg, NewEventMsg, UpdateEventMsg
from reminder.models import ChatData, EventData

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
    if len(text) == 2:
        datetime_mapping = {
            TODAY: datetime.now(timezone.utc),
            TOMORROW: datetime.now(timezone.utc) + timedelta(days=1),
            YESTERDAY: datetime.now(timezone.utc) - timedelta(days=1),
        }
        if text not in datetime_mapping:
            return None
        starting_date = datetime_mapping[text]
    elif len(text) == 4:
        try:
            starting_date = datetime.strptime(text, "%m%d")
            starting_date = starting_date.replace(year=datetime.now().year, tzinfo=timezone.utc)
        except ValueError:
            return None
    elif len(text) == 8:
        try:
            starting_date = datetime.strptime(text, "%Y%m%d")
            starting_date = starting_date.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    else:
        return None


def handle_new_event_chat(msg: str, chat_data: ChatData, conn: psycopg.Connection) -> str:
    if chat_data.chat_type == NewEventState.NAME_ENTERED:
        msg = msg.strip()
        chat_data.current_state = NewEventState.START_DATE_ENTERED
        starting_date = parse_starting_date(msg)
        if starting_date is None:
            return ErrorMsg.invalid_starting_date()
        chat_data.state_data["starting_date"] = starting_date
        update_chat(chat_data, conn)
        return NewEventMsg.prompt_for_reminder(chat_data.state_data["event_name"])

    elif chat_data.chat_type == NewEventState.START_DATE_ENTERED:
        # parse if the event needs reminder
        msg = msg.lower().strip()
        if msg == "y":
            chat_data.current_state = NewEventState.REMINDER_ENTERED
            chat_data.state_data["set_reminder"] = True
            update_chat(chat_data, conn)
            return NewEventMsg.prompt_for_cycle_time(chat_data.state_data["event_name"])
        elif msg == "n":
            chat_data.state_data["set_reminder"] = False
            chat_data.is_completed = True
            update_chat(chat_data, conn)
            new_event = EventData(
                event_id=str(uuid.uuid4()),
                event_name=chat_data.state_data["event_name"],
                user_id=chat_data.user_id,
                last_done_at=datetime.fromisoformat(chat_data.state_data["starting_date"]),
                has_reminder=False,
            )
            add_event(new_event, conn)
            return NewEventMsg.completed(chat_data.state_data["event_name"])
        else:
            return ErrorMsg.invalid_reminder_confirmation()

    elif chat_data.chat_type == NewEventState.REMINDER_ENTERED:
        # parse the reminder cycle time
        msg = msg.strip()
        try:
            cycle_count, cycle_unit = msg.split(maxsplit=1)
        except ValueError:
            return ErrorMsg.unrecognized_message()
        try:
            cycle_count = int(cycle_count)
        except ValueError:
            return ErrorMsg.invalid_cycle_period()
        if cycle_unit not in CycleUnit.SUPPORTED_UNITS:
            return ErrorMsg.invalid_cycle_period()

        chat_data.state_data["set_reminder"] = True
        chat_data.state_data["cycle_time"] = msg
        chat_data.is_completed = True
        update_chat(chat_data, conn)

        if cycle_unit == CycleUnit.DAY:
            days = cycle_count
        elif cycle_unit == CycleUnit.WEEK:
            days = cycle_count * 7
        elif cycle_unit == CycleUnit.MONTH:
            days = cycle_count * 30

        new_event = EventData(
            event_id=str(uuid.uuid4()),
            event_name=chat_data.state_data["event_name"],
            user_id=chat_data.user_id,
            last_done_at=datetime.fromisoformat(chat_data.state_data["starting_date"]),
            has_reminder=True,
            cycle_count=cycle_count,
            cycle_unit=cycle_unit,
            cycle_ends_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
        add_event(new_event, conn)
        return NewEventMsg.completed(chat_data.state_data["event_name"])


def handle_update_event_chat(data: ChatData, conn: psycopg.Connection):
    pass


def handle_edit_event_chat(data: ChatData, conn: psycopg.Connection):
    pass


def handle_delete_event_chat(data: ChatData, conn: psycopg.Connection):
    pass


def handle_ongoing_chat(msg: str, data: ChatData, conn: psycopg.Connection) -> str:
    chat_handlers = {
        ChatType.NEW_EVENT: handle_new_event_chat,
        ChatType.UPDATE_EVENT: handle_update_event_chat,
        ChatType.EDIT_EVENT: handle_edit_event_chat,
        ChatType.DELETE_EVENT: handle_delete_event_chat,
    }
    return chat_handlers[data.chat_type](msg, data, conn)


def display_event_records(event_name, user_id, conn):
    pass


def validate_command(command: str) -> str | None:
    if command not in Command.SUPPORTED_COMMANDS:
        return ErrorMsg.unrecognized_command()
    return None


def validate_event_name(event_name: str) -> str | None:
    if len(event_name) > 20:
        return ErrorMsg.event_name_invalid(too_long=True)
    bad_chars = set("/\\?*:<>|\"'`;&$(){}[]~\n\r\t\0")
    for char in event_name:
        if char in bad_chars:
            return ErrorMsg.event_name_invalid(invalid_char=char)
    return None


def handle_command(command: str, user_id: str, event_name: str, conn: psycopg.Connection):
    event_exists = get_event_id(user_id, event_name, conn) is not None
    if command == Command.NEW and event_exists:
        return ErrorMsg.event_name_duplicated(event_name)
    if command != Command.NEW and not event_exists:
        return ErrorMsg.event_not_found(event_name)
    if command == Command.FIND:
        if not event_exists:
            return ErrorMsg.event_not_found(event_name)
        return display_event_records(event_name, user_id, conn)

    chat_types = {
        Command.NEW: ChatType.NEW_EVENT,
        Command.UPDATE: ChatType.UPDATE_EVENT,
        Command.EDIT: ChatType.EDIT_EVENT,
        Command.DELETE: ChatType.DELETE_EVENT,
    }
    chat_data = ChatData(
        chat_id=str(uuid.uuid4()),
        user_id=user_id,
        chat_type=chat_types[command],
        current_state=0,
        state_data={"event_name": event_name},
    )
    add_chat(chat_data, conn)

    prompts = {
        Command.NEW: NewEventMsg.prompt_for_starting_date,
        Command.UPDATE: UpdateEventMsg.prompt_for_last_done_date,
        Command.EDIT: EditEventMsg.prompt_for_field_to_edit,
        Command.DELETE: DeleteEventMsg.prompt_for_delete_comfirmation,
    }
    return prompts[command](event_name)


def get_reply_message(msg: str, user_id: str) -> str:
    # first process with the on-going chat
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        chat_id = get_ongoing_chat_id(user_id, conn)
        if chat_id is not None:
            chat_data = get_ongoing_chat_data(chat_id, conn)
            return handle_ongoing_chat(msg, chat_data, conn)

    # if no on-going chat, then parse command from message
    try:
        command, event_name = msg.split(maxsplit=1)[0:2]
    except ValueError:
        return ErrorMsg.unrecognized_message()

    # validate command and event name
    command_validation = validate_command(command)
    if command_validation is not None:
        return command_validation
    event_name = event_name.strip()
    event_name_validation = validate_event_name(event_name)
    if event_name_validation is not None:
        return event_name_validation

    # finally, handle new command
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        return handle_command(command, user_id, event_name, conn)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    reply_message = get_reply_message(msg=event.message.text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
