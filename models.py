from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    brand_ids = relationship("MarketplaceBrand", back_populates="marketplace")


class MarketplaceBrand(Base):
    __tablename__ = "marketplace_brands"

    id = Column(Integer, primary_key=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"), nullable=False)
    brand_name = Column(String, nullable=False)
    marketplace_brand_id = Column(String, nullable=False)

    marketplace = relationship("Marketplace", back_populates="brand_ids")

    __table_args__ = (
        UniqueConstraint("marketplace_id", "brand_name", name="uq_marketplace_brand"),
    )


class CarBrand(Base):
    __tablename__ = "car_brands"

    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True, nullable=False)
    count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def __hash__(self):
        return hash(self.title)

    def __eq__(self, other):
        return isinstance(other, CarBrand) and self.title == other.title


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    year = Column(String)
    body_type = Column(String)
    transmission = Column(String)
    engine = Column(String)
    drivetrain = Column(String)
    condition = Column(String)
    color = Column(String)
    availability = Column(String)
    mileage = Column(String)
    brand = Column(String)
    model = Column(String)
    generation = Column(String)
    modification = Column(String)
    price = Column(Integer)
    price_local_currency = Column(Integer)
    description = Column(String)

    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow, onupdate=utcnow)
    sold_at = Column(DateTime, nullable=True)

    price_histories = relationship("CarPriceHistory", back_populates="car")
    snapshots = relationship("CarSnapshot", back_populates="car")
    images = relationship("CarImage", back_populates="car")


class CarPriceHistory(Base):
    __tablename__ = "car_price_histories"

    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    price = Column(Integer)
    price_local_currency = Column(Integer)
    fetched_at = Column(DateTime, default=utcnow)

    car = relationship("Car", back_populates="price_histories")


class CarSnapshot(Base):
    __tablename__ = "car_snapshots"

    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    characteristics = Column(JSON)
    snapshot_hash = Column(String)
    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow, onupdate=utcnow)

    car = relationship("Car", back_populates="snapshots")


class CarImage(Base):
    __tablename__ = "car_images"

    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=False)
    sha256 = Column(String)
    storage_key = Column(String)
    source_url = Column(String)
    created_at = Column(DateTime, default=utcnow)

    car = relationship("Car", back_populates="images")


