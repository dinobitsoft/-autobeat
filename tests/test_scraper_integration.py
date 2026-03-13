import pytest
from datetime import datetime
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from autobeat import Base, store_data, Car, CarPriceHistory, CarSnapshot

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture
def engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_insert_new_car(engine):
    url = "https://test/car/1"
    price = 20000
    characteristics = {"engine": "electric"}

    store_data(url, price, characteristics, engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    car = session.query(Car).filter_by(url=url).first()

    assert car is not None

    prices = session.query(CarPriceHistory).filter_by(car_id=car.id).all()
    snapshots = session.query(CarSnapshot).filter_by(car_id=car.id).all()

    assert len(prices) == 1
    assert prices[0].price == str(price)

    assert len(snapshots) == 1
    assert snapshots[0].characteristics == characteristics

    session.close()


def test_price_history_insert_only_on_change(engine):
    url = "https://test/car/2"
    characteristics = {"engine": "electric"}

    store_data(url, 20000, characteristics, engine)
    store_data(url, 20000, characteristics, engine)
    store_data(url, 21000, characteristics, engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    car = session.query(Car).filter_by(url=url).first()

    prices = (
        session.query(CarPriceHistory)
        .filter_by(car_id=car.id)
        .order_by(CarPriceHistory.fetched_at)
        .all()
    )

    assert len(prices) == 2
    assert prices[0].price == "20000"
    assert prices[1].price == "21000"

    session.close()


def test_snapshot_updates_timestamp_if_same(engine):
    url = "https://test/car/3"
    price = 20000
    characteristics = {"engine": "electric"}

    store_data(url, price, characteristics, engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    car = session.query(Car).filter_by(url=url).first()
    snapshot1 = session.query(CarSnapshot).filter_by(car_id=car.id).first()
    first_last_seen = snapshot1.last_seen_at

    session.close()

    store_data(url, price, characteristics, engine)

    session = Session()
    snapshot2 = session.query(CarSnapshot).filter_by(car_id=car.id).first()

    assert snapshot2.last_seen_at >= first_last_seen
    assert session.query(CarSnapshot).filter_by(car_id=car.id).count() == 1

    session.close()


def test_snapshot_insert_on_change(engine):
    url = "https://test/car/4"
    price = 20000

    store_data(url, price, {"engine": "electric"}, engine)
    store_data(url, price, {"engine": "diesel"}, engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    car = session.query(Car).filter_by(url=url).first()

    snapshots = (
        session.query(CarSnapshot)
        .filter_by(car_id=car.id)
        .order_by(CarSnapshot.first_seen_at)
        .all()
    )

    assert len(snapshots) == 2
    assert snapshots[0].characteristics["engine"] == "electric"
    assert snapshots[1].characteristics["engine"] == "diesel"

    session.close()