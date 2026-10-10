# create_tables.py
from models import Base
from db import engine

Base.metadata.create_all(engine)
print("✅ Sab tables ban gaye!")