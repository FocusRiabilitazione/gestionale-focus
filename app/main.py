from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlmodel import SQLModel 
from datetime import date

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- 1. CONFIGURAZIONE PAZIENTI ---
class PazienteAdmin(ModelView, model=Paziente):
    # ESTETICA: Qui correggiamo i nomi e le icone
    name = "Paziente"
    name_plural = "Pazienti"  # Addio alla "s"!
    icon = "fa-solid fa-user-injured"
    
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.area,
        Paziente.disdetto,
        Paziente.data_disdetta
    ]
    
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    column_filters = [Paziente.area, Paziente.disdetto]

    # Menu a tendina e Action sono disattivati per capire se erano loro il problema
    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

# --- 2. ALTRE VISTE (Estetica curata) ---

class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"
    column_list = [Inventario.materiale, Inventario.quantita, Inventario.area_stanza]

class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-hand-holding"
    column_list = [Prestito.oggetto, Prestito.paziente_nome, Prestito.restituito]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-invoice-dollar"
    column_list = [Preventivo.data_creazione, Preventivo.paziente, Preventivo.totale]

class ScadenzaAdmin(ModelView, model=Scadenza):
    name = "Scadenza"
    name_plural = "Scadenzario"
    icon = "fa-solid fa-calendar"
    column_list = [Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# --- 3. ATTIVAZIONE ---
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
    return {"msg": "Gestionale Focus Rehab - Estetica Attiva"}
