"""
Подключение к базе данных
"""
from sqlalchemy import create_engine
import config

engine = create_engine(
    config.DB_CONNECTION_STRING,
    echo=True,
    connect_args={"ssl": {"ssl_disabled": False}},
)
