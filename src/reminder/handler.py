import logging

import psycopg
import requests
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent, UnfollowEvent

from reminder.const import DATABASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from reminder.db import add_user, delete_user

logger = logging.getLogger(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@handler.add(FollowEvent)
def handle_follow_event(event: FollowEvent) -> None:
    user_id = event.source.user_id
    resp = requests.get(f"https://api.line.me/v2/bot/profile/{user_id}")
    user_info = resp.json()
    display_name = user_info.get("displayName")
    picture_url = user_info.get("pictureUrl")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        add_user(user_id=user_id, display_name=display_name, picture_url=picture_url, conn=conn)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="hello my new friend!")])
        )

    logger.info(f"Added (or unblocked) by: {user_id}")
    logger.info(f"Display name: {display_name}")


@handler.add(UnfollowEvent)
def handle_unfollow_event(event: UnfollowEvent) -> None:
    user_id = event.source.user_id
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        delete_user(user_id=user_id, conn=conn)

    logger.info(f"Blocked by: {user_id}")


def get_reply_message(msg: str, user_id: str):
    return "abcd"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    reply_message = get_reply_message(msg=event.message.text, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_message)])
        )
