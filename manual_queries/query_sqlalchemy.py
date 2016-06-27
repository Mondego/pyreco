"""Relevant method:configure"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///orm_in_detail.sqlite')
 
session = sessionmaker()
session.
