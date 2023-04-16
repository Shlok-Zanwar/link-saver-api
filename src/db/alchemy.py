import os
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

cdb = None
DBSession: sessionmaker = None
Base = None


class Settings:
    PROJECT_NAME: str = "Cian"
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_SERVER: str = os.getenv("DB_SERVER", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", 5432)  # default postgres port is 5432
    DB_DB: str = os.getenv("DB_DB", "tdd")
    # DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DB}"
    # DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DB}"
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DB}"



settings = Settings()

engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 2}, pool_size=0, max_overflow=-1,)


try:
    Base = automap_base()
    Base.prepare(engine, reflect=True)
    logger.info("Database connected successfully")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as err:
    logger.error("Database Connection Error - {}".format(err))
