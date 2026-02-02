# =============================================================================
# db.py - Database Configuration
# =============================================================================
# SQLAlchemy database engine and session configuration.
#
# PROVIDES:
# - engine: SQLAlchemy engine connected to PostgreSQL
# - SessionLocal: Session factory for database operations
# - Base: Declarative base for ORM models
# - get_db(): Dependency for FastAPI route injection
#
# USAGE:
#   from .db import get_db, engine, Base
#   
#   # In FastAPI routes:
#   def my_route(db: Session = Depends(get_db)):
#       ...
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings


# =============================================================================
# DATABASE ENGINE
# =============================================================================
DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, echo=False, future=True)


# =============================================================================
# SESSION FACTORY
# =============================================================================
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


# =============================================================================
# DECLARATIVE BASE
# =============================================================================
Base = declarative_base()


# =============================================================================
# DEPENDENCY - get_db()
# =============================================================================
def get_db():
    """
    Dependency that provides a database session.
    
    Usage in FastAPI routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    The session is automatically closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
