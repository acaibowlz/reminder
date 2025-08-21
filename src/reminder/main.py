import logging

import psycopg
from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration

import reminder.event_handlers
from reminder.const import DATABASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from reminder.db import init_db

logger = logging.getLogger(__name__)

with psycopg.connect(conninfo=DATABASE_URL) as conn:
    init_db(conn)

app = FastAPI()

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


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
