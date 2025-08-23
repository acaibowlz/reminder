import logging

import psycopg
from fastapi import FastAPI, HTTPException, Request, status
from linebot.v3.exceptions import InvalidSignatureError

from reminder.const import DATABASE_URL
from reminder.db import init_db
from reminder.handler import handler
from reminder.logging import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

with psycopg.connect(conninfo=DATABASE_URL) as conn:
    init_db(conn)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    """
    The entry point of out LINE bot.
    """
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Line-Signature header not found")

    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature. Please check your channel secret and access token.",
        )
    except Exception as e:
        logger.error(str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

    return "OK"
