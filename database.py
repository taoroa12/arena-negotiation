import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

STORAGE_DIR = "/app/storage" if os.path.isdir("/app/storage") else "."
DATABASE_URL = f"sqlite:///{STORAGE_DIR}/arena.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()