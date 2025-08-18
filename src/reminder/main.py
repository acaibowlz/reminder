import logging

from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .config import settings

logger = logging.getLogger(__name__)

app = FastAPI()

configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=event.source)])
        )


@app.post("/webhook")
async def webhook(request: Request):
    """
    LINE Webhook 主入口。
    驗證簽名並將事件分派給對應的處理器。
    """
    # 1. 從標頭取得簽名
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=400, detail="X-Line-Signature header not found")

    # 2. 取得請求的 body
    body = await request.body()

    # 3. 交給 line-bot-sdk 的 handler 進行驗證和處理
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        # 簽名驗證失敗，回傳 400
        raise HTTPException(
            status_code=400, detail="Invalid signature. Please check your channel secret and access token."
        )
    except Exception as e:
        # 其他所有未預期的錯誤，回傳 500
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # 4. 如果一切順利，回傳 200 OK
    return "OK"
