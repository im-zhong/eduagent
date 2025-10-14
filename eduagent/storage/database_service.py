from sqlalchemy import Engine
from sqlalchemy.orm import Session


class DatabaseService:
    def __init__(self, engine: Engine) -> None:
        self.engine: Engine = engine

    def _new_session(self) -> Session:
        return Session(bind=self.engine)

    # TODO: Add methods for common database operations (CRUD)
