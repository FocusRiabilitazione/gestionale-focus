from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel 
from datetime import date
from wtforms import SelectField # <--- IMPORTANTE: Serve per il menu a tendina

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PAZIENTI (Versione AVANZATA) ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    # Lista colonne (Cosa vedi nella tabella)
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.area,
        Paziente.disdetto,
        Paziente.data_disdetta
    ]
    
    # Aggiungo la ricerca e i filtri (Comodissimi)
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    column_filters = [Paziente.area, Paziente.disdetto]

    # --- 1. MENU A TENDINA (AREA) ---
    form_overrides = dict(area=SelectField)
    form_args = dict(area=dict(
        choices=["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico"],
        label="Area di Competenza"
    ))

    # Form di inserimento ordinato
    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

    # --- 2. AZIONE RAPIDA DISDETTA ---
    @action(
        name="segna_disdetto",
        label="❌ Segna come Disdetto",
        confirmation_message="Confermi la disdetta? Verrà inserita la data di oggi."
    )
    async def action_disdetto(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        if pks and pks != ['']:
            with self.session_maker() as session:
                for pk in pks:
                    model = session.get(Paziente, int(pk))
                    if model:
                        model.disdetto = True
                        model.data_disdetta = date.today()
                        session.add(model)
                session.commit()
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
    return {"msg": "Gestionale Focus Rehab Attivo"}
