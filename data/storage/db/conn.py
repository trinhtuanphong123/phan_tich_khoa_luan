import sqlite3
import os

NEWS_DB_PATH = os.getenv("NEWS_DB_PATH", "data/news.db")


def connect(db_path: str = NEWS_DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con
