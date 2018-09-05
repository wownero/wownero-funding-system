from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

import settings


def create_session():
    from funding.orm.orm import base
    engine = sa.create_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False, encoding="latin")
    session = scoped_session(sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=engine))
    base.query = session.query_property()
    base.metadata.create_all(bind=engine)
    return session