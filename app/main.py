from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel 
from datetime import date

# 1. SETUP DATABASE
from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- CONFIGURAZIONE PAZIENTI ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
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

    # --- MENU A TENDINA (METODO SICURO) ---
    # Mostra un menu a tendina anche se il database usa stringhe semplici
    form_args = dict(
        area=dict(
            choices=[
                ("Mano-Polso", "Mano-Polso"),
                ("Colonna", "Colonna"),
                ("ATM", "ATM"),
                ("Muscolo-Scheletrico", "Muscolo-Scheletrico")
            ],
            label="Area di Competenza"
        )
    )

    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

    # AZIONE DISDETTA
    @action(
        name="segna_disdetto",
        label="❌ Segna come Disdetto",
        confirmation_message="Confermi la disdetta?"
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

# --- ALTRE VISTE (Definite CORRETTAMENTE) ---
# Qui era l'errore: ora usiamo le classi esplicite
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
    column_list = [Scadenza.data_scadenza, Scadenza.descrizione, Scadenza.importo]

# ATTIVAZIONE ADMIN
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

# --- TASTO EMERGENZA (NUKE) ---
# Se qualcosa va storto, apri: /nuke-database
@app.get("/nuke-database")
def nuke_db():
    try:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        return {"status": "SUCCESS: Database resettato da zero."}
    except Exception as e:
        return {"error": str(e)}
