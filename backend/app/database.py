import logging
import os
import shutil
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = Path(__file__).resolve().parents[1]
SEED_DATABASE_PATH = BACKEND_DIR / "data" / "app.db"
logger = logging.getLogger(__name__)


def initialize_database(target: Path, seed: Path = SEED_DATABASE_PATH) -> Path:
    target = target.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() and seed.exists() and target != seed.resolve():
        shutil.copy2(seed, target)
        logger.info("Seed database copied to %s", target)
    logger.info("Using database file %s", target)
    return target


configured_path = (os.getenv("DATABASE_PATH") or "").strip()
DATABASE_PATH = initialize_database(Path(configured_path) if configured_path else SEED_DATABASE_PATH)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
