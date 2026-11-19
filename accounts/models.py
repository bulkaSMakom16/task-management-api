from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from config.database import Base, utc_now


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="unique_username"),)

    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
