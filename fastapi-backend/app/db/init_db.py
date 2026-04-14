from app.db.session import engine
from app.db.base import Base


def init_db() -> None:
    # Creates tables based on models (use Alembic for real migrations)
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
