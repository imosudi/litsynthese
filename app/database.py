import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database URL configuration (configurable via environment variables)
# Defaults to a local SQLite database file in the workspace directory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./litsynthese.db")

# SQLite connection requirements for multi-threaded FastAPI usage
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create connection engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False  # Set to True for SQL queries logging
)

# Session factory for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base class for models (SQLAlchemy 2.0+ standard style)
class Base(DeclarativeBase):
    pass

# Dependency helper function to yield database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
