from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import SQLITE_URL

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # import models here to register them with metadata
    from . import models
    Base.metadata.create_all(bind=engine)
