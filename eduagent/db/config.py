# from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        self.database_url = database_url
        self.echo = echo
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker[Session] | None = None

    def init_engine(self) -> None:
        """Initialize database engine"""
        if "sqlite" in self.database_url:
            self.engine = create_engine(
                self.database_url,
                echo=self.echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(
                self.database_url, echo=self.echo, pool_pre_ping=True, pool_recycle=300
            )

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self) -> None:
        """Create all database tables"""
        if not self.engine:
            self.init_engine()

        assert self.engine is not None
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables"""
        if not self.engine:
            self.init_engine()

        assert self.engine is not None
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session"""
        if not self.SessionLocal:
            self.init_engine()

        assert self.SessionLocal is not None
        return self.SessionLocal()

    def get_session_factory(self) -> sessionmaker[Session]:
        """Get session factory for dependency injection"""
        if not self.SessionLocal:
            self.init_engine()

        assert self.SessionLocal is not None
        return self.SessionLocal


# Default configuration
default_config = DatabaseConfig(database_url="sqlite:///./eduagent.db", echo=False)
