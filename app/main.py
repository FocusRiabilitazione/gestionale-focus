from fastapi import FastAPI
from sqladmin import Admin, ModelView
from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PANNELLO AMMINISTRAZIONE ---

class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured" # Icona più adatta
    
    # Cosa vedere nella lista principale (Colonne)
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.telefono, 
        Paziente.area, 
        Paziente.disdetto
    ]
    
    # Barra di Ricerca (Cerca per nome, cognome o CF)
    column_searchable_list = [Paziente.cognome, Paziente.nome, Paziente.codice_fiscale]
    
    # Filtri laterali (Es: "Fammi vedere solo quelli Disdetti")
    column_filters = [Paziente.area, Paziente.disdetto, Paziente.visita_esterna]
    
    # Ordine di default (Alfabetico per Cognome)
    column_default_sort = ("cognome", False) 

    # Organizzazione del Form di inserimento (Raggruppiamo i campi)
    form_columns = [
        Paziente.nome, Paziente.cognome, Paziente.codice_fiscale,
        Paziente.telefono, Paziente.email, Paziente.area,
        Paziente.note,
        Paziente.disdetto, Paziente.data_disdetta,
        Paziente.visita_esterna, Paziente.data_visita
    ]

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

