from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine


class PGSQLSettings(BaseModel):
    username: str = Field(..., title="Postgres User")
    password: str = Field(..., title="Postgres Password")
    host: str = Field(..., title="Postgres Host")
    port: int = Field(..., title="Postgres Port")
    database: str = Field(..., title="Postgres Database")

    def get_pgsql_url(self) -> str:
        return f"postgresql+psycopg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


# https://docs.sqlalchemy.org/en/20/tutorial/engine.html#tutorial-engine
# This object acts as a central source of connections to a particular database,
# providing both a factory as well as a holding space called a connection pool for these database connections.
#  The engine is typically a global object created just once for a particular database server,
# and is configured using a URL string which will describe how it should connect to the database host or backend.
def create_pgsql_engine(pgsql_settings: PGSQLSettings) -> Engine:
    return create_engine(pgsql_settings.get_pgsql_url(), echo=True)
