import logging
import sys

from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .config import const

logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.INFO)
formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")
logger.addHandler(stream_handler)

app = FastAPI()

configuration = Configuration(access_token=const.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(const.LINE_CHANNEL_SECRET)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=str(event.source.user_id))])
        )


@app.post("/webhook")
async def webhook(request: Request):
    """
    LINE Webhook 主入口。
    驗證簽名並將事件分派給對應的處理器。
    """
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=400, detail="X-Line-Signature header not found")

    # 2. 取得請求的 body
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=400, detail="Invalid signature. Please check your channel secret and access token."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return "OK"
