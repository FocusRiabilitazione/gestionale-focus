from sqlmodel import SQLModel, create_engine, Session, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lettere_store.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

def init_db():
    SQLModel.metadata.create_all(engine)
    _migrate()

def _migrate():
    """Aggiunge le nuove colonne al DB esistente senza perdere dati."""
    new_columns = [
        ("ALTER TABLE ordini_lettere ADD COLUMN tema_nome VARCHAR", None),
        ("ALTER TABLE ordini_lettere ADD COLUMN tema_emoji VARCHAR", None),
        ("ALTER TABLE ordini_lettere ADD COLUMN elementi_scelti VARCHAR", None),
        ("ALTER TABLE ordini_lettere ADD COLUMN prezzo_elementi FLOAT DEFAULT 0.0", None),
    ]
    with engine.connect() as conn:
        for sql, _ in new_columns:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # colonna già esistente

def get_session():
    with Session(engine) as session:
        yield session
