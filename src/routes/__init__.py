from loguru import logger as logging
from pydantic import BaseModel
from datetime import datetime
import psycopg2.extras


class Message(BaseModel):
    status_code: int
    detail: str


def get_db():
    '''
    does
    :return:
    '''
    from src.db.alchemy import SessionLocal, engine

    db = SessionLocal()
    # logging.info("get_db")
    try:
        # logging.debug("yeilding db")
        yield db
    finally:
        # logging.debug("closing db")
        db.close()


def get_raw_db():
    '''
    does
    :return:
    '''
    from src.db.alchemy import SessionLocal, engine

    db = engine.raw_connection()


    # logging.info("get_db")
    try:
        # logging.debug("yeilding db")
        yield db
    finally:
        # logging.debug("closing db")
        db.close()

