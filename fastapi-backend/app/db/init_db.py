from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    # Creates tables based on models (use Alembic for real migrations)
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
