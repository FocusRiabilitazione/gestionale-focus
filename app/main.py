from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqlmodel import select
from wtforms import SelectField # Per il menu a tendina
from datetime import date

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PAZIENTI AVANZATA ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    # Colonne visibili nella lista
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.area, 
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]
    
    # Ricerca e Filtri
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    column_filters = [Paziente.area, Paziente.disdetto]
    column_default_sort = ("cognome", False)

    # --- 1. CONFIGURAZIONE MENU A TENDINA (AREA) ---
    # Questo obbliga a scegliere tra queste opzioni precise
    form_overrides = dict(area=SelectField)
    form_args = dict(area=dict(
        choices=["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico"],
        label="Area di Competenza (Obbligatorio)"
    ))

    # Ordine dei campi nel form di creazione
    form_columns = [
        Paziente.nome, Paziente.cognome, Paziente.area,
        Paziente.telefono, Paziente.email, Paziente.codice_fiscale,
        Paziente.note,
        Paziente.disdetto, Paziente.data_disdetta
    ]

    # --- 2. AZIONE AUTOMATICA "DISDETTA" ---
    # Questo crea un pulsante nel menu "Actions"
    @action(
        name="segna_disdetto",
        label="❌ Segna come Disdetto",
        confirmation_message="Vuoi segnare i pazienti selezionati come Disdetti? Verrà inserita la data di oggi."
    )
    async def action_disdetto(self, request: Request):
        # Recupera gli ID selezionati
        pks = request.query_params.get("pks", "").split(",")
        if pks:
            with self.session_maker() as session:
                for pk in pks:
                    # Trova il paziente
                    model = session.get(Paziente, int(pk))
                    if model:
                        # APPLICA LA LOGICA AUTOMATICA
                        model.disdetto = True
                        model.data_disdetta = date.today() # Data di OGGI automatica
                        session.add(model)
                session.commit()
        # Ricarica la pagina
        return

# --- ALTRE VISTE (Standard) ---

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
    return {"msg": "Gestionale Focus Rehab"}
