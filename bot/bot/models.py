from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(100), nullable=False, index=True)
    model = Column(Text, nullable=False)
    year = Column(Integer, nullable=True)
    price = Column(Integer, nullable=True)
    color = Column(String(100), nullable=True)
    url = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
