from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


url = get_settings().database_url
engine = create_engine(
    url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}, pool_pre_ping=True
)
if url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
