from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session
from datetime import date
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURA PER IMPORTAZIONE MASSIVA ---
class PazienteImport(BaseModel):
    nome: str
    cognome: str
    area: str 

# --- CONFIGURAZIONE PAZIENTI ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    # ESTETICA: Spunta verde e Stetoscopio
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }

    # LISTA (Cosa vedi nella tabella principale)
    column_list = [
        Paziente.cognome, 
        Paziente.nome, 
        Paziente.area,
        Paziente.visita_medica, 
        Paziente.data_visita,
        Paziente.disdetto,
        Paziente.data_disdetta
    ]
    
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    
    # FORM (Cosa vedi quando apri/modifichi)
    # ⚠️ HO TOLTO LE SCRITTE "SEZIONE..." CHE CAUSAVANO L'ERRORE
    form_columns = [
        Paziente.nome, 
        Paziente.cognome, 
        Paziente.area,
        Paziente.note,
        Paziente.visita_medica,
        Paziente.data_visita, 
        Paziente.disdetto, 
        Paziente.data_disdetta
    ]

    # AZIONE TASTO DISDETTA
    @action(
        name="segna_disdetto",
        label="❌ Segna come Disdetto",
        confirmation_message="Confermi la disdetta? Verrà inserita la data di oggi."
    )
    def action_disdetto(self, request: Request):
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

# --- IMPORTAZIONE RAPIDA ---
@app.post("/import-rapido")
def import_pazienti(lista_pazienti: List[PazienteImport]):
    try:
        count = 0
        with Session(engine) as session:
            for p in lista_pazienti:
                nuovo = Paziente(
                    nome=p.nome, 
                    cognome=p.cognome, 
                    area=p.area 
                )
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} pazienti correttamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Corretto"}
