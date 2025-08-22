import configparser
from contextlib import asynccontextmanager
from typing import *
import os
import aiomysql


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            minsize=5,
            maxsize=30,
            autocommit=True
        )

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()

    @asynccontextmanager
    async def get_connection(self):
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)


db = Database()
