from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlmodel import SQLModel

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- DEFINIZIONE VISTE (SENZA ERRORI) ---
# Non metto icone o cose strane, solo il modello base.

class PazienteAdmin(ModelView, model=Paziente):
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]

class InventarioAdmin(ModelView, model=Inventario):
    column_list = [Inventario.materiale, Inventario.quantita]

class PrestitoAdmin(ModelView, model=Prestito):
    column_list = [Prestito.paziente_nome, Prestito.oggetto]

class PreventivoAdmin(ModelView, model=Preventivo):
    column_list = [Preventivo.paziente, Preventivo.totale]

class ScadenzaAdmin(ModelView, model=Scadenza):
    column_list = [Scadenza.descrizione, Scadenza.data_scadenza]

# --- ATTIVAZIONE ---
admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def home():
    return {"msg": "Gestionale ATTIVO - Modalità Sicura"}
