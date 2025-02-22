import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.constants import DATABASE_URI


class Base(DeclarativeBase):
    pass


os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URI)
make_session = sessionmaker(engine, expire_on_commit=False)
