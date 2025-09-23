from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        self.echo = echo
        self.engine = None
        self.SessionLocal = None

    def init_engine(self):
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

    def create_tables(self):
        """Create all database tables"""
        if not self.engine:
            self.init_engine()

        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all database tables"""
        if not self.engine:
            self.init_engine()

        Base.metadata.drop_all(bind=self.engine)

    def get_session(self):
        """Get database session"""
        if not self.SessionLocal:
            self.init_engine()

        return self.SessionLocal()

    def get_session_factory(self):
        """Get session factory for dependency injection"""
        if not self.SessionLocal:
            self.init_engine()

        return self.SessionLocal


# Default configuration
default_config = DatabaseConfig(database_url="sqlite:///./eduagent.db", echo=False)
