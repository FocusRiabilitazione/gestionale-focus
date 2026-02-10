import os
from sqlmodel import create_engine, SQLModel

db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, echo=False)

def init_db():
    # --- COMANDO DI RESET ---
    # Cancella tutto il vecchio database (sblocca l'errore)
    SQLModel.metadata.drop_all(engine)
    
    # Crea le nuove tabelle pulite
    SQLModel.metadata.create_all(engine)
