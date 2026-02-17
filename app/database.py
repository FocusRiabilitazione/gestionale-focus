import os
from sqlmodel import create_engine, SQLModel

# Recupera l'indirizzo del database da Railway
db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Crea il motore del database
engine = create_engine(db_url, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)
