import logging

import psycopg
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from linebot.v3.exceptions import InvalidSignatureError

from routine_bot.constants import DATABASE_URL, LOGGING_CONFIG, REMINDER_TOKEN
from routine_bot.db import init_db
from routine_bot.handlers import handler

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

    return Response(status_code=status.HTTP_200_OK)


@app.post("/reminder/run")
async def run_reminder(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ")[1]
    if token != REMINDER_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        pass
