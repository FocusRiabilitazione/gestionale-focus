from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel 
from datetime import date
from starlette.responses import RedirectResponse # <--- QUESTO RISOLVE L'ERRORE DEL TASTO

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
    
    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

    # --- 1. INTELLIGENZA DI SALVATAGGIO (Risolve il problema della data che resta) ---
    async def on_model_change(self, data, model, is_created, request):
        # Se l'utente ha messo la spunta Disdetto ma non la data -> Metti oggi
        if model.disdetto is True and model.data_disdetta is None:
            model.data_disdetta = date.today()
            
        # Se l'utente ha TOLTO la spunta Disdetto -> Cancella la data
        if model.disdetto is False:
            model.data_disdetta = None
            
        # Ora il sistema salverà il modello corretto

    # --- 2. AZIONE TASTO DISDETTA (Risolve l'errore rosso) ---
    @action(
        name="segna_disdetto",
        label="❌ Segna come Disdetto",
        confirmation_message="Confermi la disdetta? Verrà inserita la data di oggi."
    )
    async def action_disdetto(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        
        with self.session_maker() as session:
            for pk in pks:
                if pk.isdigit():
                    model = session.get(Paziente, int(pk))
                    if model:
                        model.disdetto = True
                        model.data_disdetta = date.today()
                        session.add(model)
            session.commit()

        # TRUCCO FINALE: Invece di restituire testo, ricarichiamo la pagina.
        # Questo forza il browser a chiudere il popup e mostrare i dati nuovi.
        return RedirectResponse(request.url_for("admin:list", identity="paziente"), status_code=303)

# --- ALTRE VISTE ---
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
    return {"msg": "Gestionale Focus Rehab - Versione Stabile"}
