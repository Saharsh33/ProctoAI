import enum

from sqlalchemy import Column, BigInteger, String, Text, SmallInteger, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class Role(str, enum.Enum):
    ROLE_ADMIN = "admin"
    ROLE_STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    uid = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    register_time = Column(TIMESTAMP, server_default=func.now())
    user_type = Column(String(25), nullable=False)  # student / admin
    user_image = Column(Text, nullable=False)
    user_login = Column(SmallInteger, default=0)
    examcredits = Column(Integer, default=7)