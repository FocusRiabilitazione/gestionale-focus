import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Field, create_engine, text
from datetime import date
from typing import Optional

# --- 1. SETUP DATABASE ---
import os
db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, echo=False)

# --- 2. MODELLI (SEMPLIFICATI AL MASSIMO) ---
class Paziente(SQLModel, table=True):
    __tablename__ = "paziente_finale" # Nome definitivo
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: str  # Solo testo per ora, per sicurezza
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None

class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    quantita: int = 0
    area_stanza: str

class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    paziente_nome: str
    data_scadenza: date
    restituito: bool = False

class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    totale: float
    data_creazione: date = Field(default_factory=date.today)

class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    data_scadenza: date
    importo: float
    pagato: bool = False

# --- 3. APP E DIAGNOSTICA ---
app = FastAPI(title="Gestionale Focus Rehab - DIAGNOSTICA")

# QUESTO È IL PEZZO MAGICO:
# Se c'è un errore, te lo mostra invece di dire "Server Error"
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_msg = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "ERRORE RILEVATO", "error": str(e), "traceback": error_msg}
        )

# --- 4. CONFIGURAZIONE ADMIN ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user"
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]
    
    # Menu a tendina visuale (non tocca il DB)
    form_args = dict(
        area=dict(
            choices=[("Mano", "Mano"), ("Colonna", "Colonna"), ("ATM", "ATM")],
            label="Area"
        )
    )

admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
# Aggiungo le altre viste base
admin.add_view(ModelView(Inventario, icon="fa-solid fa-box"))
admin.add_view(ModelView(Prestito, icon="fa-solid fa-hand-holding"))
admin.add_view(ModelView(Preventivo, icon="fa-solid fa-file-invoice"))
admin.add_view(ModelView(Scadenza, icon="fa-solid fa-calendar"))

@app.on_event("startup")
def on_startup():
    # Crea le tabelle se non esistono
    SQLModel.metadata.create_all(engine)

@app.get("/")
def home():
    return {"status": "ONLINE", "msg": "Vai su /admin. Se vedi errori, copiali e mandali."}

# --- 5. PULIZIA TOTALE (NUCLEAR) ---
@app.get("/nuke-database")
def nuke_db():
    try:
        # Tenta di cancellare tutto brutalmente
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        return {"status": "DB PULITO. Ora è tutto vuoto e nuovo."}
    except Exception as e:
        return {"error": str(e)}
