from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings, ROOT_DIR
from pathlib import Path

# Resolve SQLite database path reliably across working directories
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///../"):
    relative_path = db_url.replace("sqlite:///../", "")
    target_path = (ROOT_DIR / relative_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{target_path.as_posix()}"
elif db_url.startswith("sqlite:///./"):
    relative_path = db_url.replace("sqlite:///./", "")
    target_path = (ROOT_DIR / relative_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{target_path.as_posix()}"
elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
    raw_path = db_url.replace("sqlite:///", "")
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)

from sqlalchemy.pool import NullPool

engine = create_engine(
    db_url,
    poolclass=NullPool if "sqlite" in db_url else None,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
