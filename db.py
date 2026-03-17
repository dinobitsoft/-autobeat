from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from config import POSTGRES_URL

engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

Session = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)