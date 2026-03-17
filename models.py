from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime

Base = declarative_base()


class Car(Base):

    __tablename__ = "cars"

    id = Column(Integer, primary_key=True)

    source_url = Column(String, unique=True)

    first_seen = Column(DateTime, default=datetime.utcnow)

    last_seen = Column(DateTime, default=datetime.utcnow)


class CarSnapshot(Base):

    __tablename__ = "car_snapshots"

    id = Column(Integer, primary_key=True)

    car_id = Column(Integer, ForeignKey("cars.id"))

    price = Column(Integer)

    characteristics = Column(JSON)

    snapshot_hash = Column(String)

    first_seen = Column(DateTime, default=datetime.utcnow)

    last_seen = Column(DateTime, default=datetime.utcnow)


class CarImage(Base):

    __tablename__ = "car_images"

    id = Column(Integer, primary_key=True)

    car_id = Column(Integer)

    sha256 = Column(String)

    storage_key = Column(String)

    source_url = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)