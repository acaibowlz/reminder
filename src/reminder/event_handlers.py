import psycopg
from linebot.v3.messaging import ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent

from reminder.const import DATABASE_URL
from reminder.db import add_user
from reminder.main import configuration, handler


@handler.add(FollowEvent)
def handle_added_as_friend(event: FollowEvent) -> None:
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        add_user(conn, user_id=event.source.user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="hello my new friend!")])
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent) -> None:
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=str(event.message.text))])
        )
