from fastapi import FastAPI
from sqladmin import Admin, ModelView
from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PANNELLO AMMINISTRAZIONE ---

class PazienteAdmin(ModelView, model=Paziente):
    # Qui impostiamo i nomi italiani corretti
    name = "Paziente"
    name_plural = "Pazienti"
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    icon = "fa-solid fa-user"

class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    column_list = [Inventario.materiale, Inventario.quantita, Inventario.area_stanza, Inventario.soglia_minima]
    column_sortable_list = [Inventario.quantita]
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

# --- AVVIO ---
@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def home():
    return {"message": "Sistema Focus Rehab Attivo. Vai su /admin per accedere."}
