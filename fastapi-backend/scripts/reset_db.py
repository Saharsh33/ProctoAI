"""
Database reset script for development.

This script drops all tables and recreates them using SQLAlchemy models.
Use this when you encounter schema conflicts or want a fresh database.

WARNING: This will DELETE ALL DATA in your database!
Only use this in development environments.
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine
from app.db.base import Base
import app.models  # noqa: F401 - Import all models to register them


def reset_database():
    """Drop all tables and recreate them."""
    print("WARNING: This will delete all data in the database!")
    print(f"Database: {engine.url}")

    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    print("\n1. Dropping all tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("   ✓ All tables dropped successfully")
    except Exception as e:
        print(f"   ✗ Error dropping tables: {e}")
        return

    print("\n2. Creating all tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✓ All tables created successfully")
    except Exception as e:
        print(f"   ✗ Error creating tables: {e}")
        return

    print("\n✓ Database reset completed successfully!")
    print("\nNext steps:")
    print("  - Run your application: uvicorn app.main:app --reload")
    print("  - Or use Alembic for migrations: alembic upgrade head")


if __name__ == "__main__":
    reset_database()