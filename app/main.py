from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel 
from datetime import date

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PAZIENTI (Versione BASE Sicura) ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    # Lista semplice
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.area,
        Paziente.disdetto
    ]
    
    # Form semplice (Senza menu a tendina per ora, per testare se funziona)
    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

# --- ALTRE VISTE ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    column_list = [Inventario.materiale, Inventario.quantita, Inventario.area_stanza]
    icon = "fa-solid fa-box"

class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    column_list = [Prestito.oggetto, Prestito.paziente_nome, Prestito.data_scadenza, Prestito.restituito]
    icon = "fa-solid fa-hand-holding"

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    column_list = [Preventivo.data_creazione, Preventivo.paziente, Preventivo.totale]
    icon = "fa-solid fa-file-invoice-dollar"

class ScadenzaAdmin(ModelView, model=Scadenza):
    name = "Scadenza"
    name_plural = "Scadenzario"
    column_list = [Scadenza.data_scadenza, Scadenza.descrizione, Scadenza.importo, Scadenza.pagato]
    icon = "fa-solid fa-calendar"

# Attivazione Admin
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
    return {"msg": "Gestionale Focus Rehab Attivo"}
