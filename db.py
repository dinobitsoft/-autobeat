from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import POSTGRES_URL

engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

Session = sessionmaker(bind=engine)


def get_session():
    return Session()


def init_db():
    from models import Base
    Base.metadata.create_all(engine)