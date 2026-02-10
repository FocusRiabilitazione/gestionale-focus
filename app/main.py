from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta # <--- Ho aggiunto timedelta per i calcoli
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURE PER IMPORTAZIONE MASSIVA ---

# 1. Per i Pazienti
class PazienteImport(BaseModel):
    nome: str
    cognome: str
    area: str

# 2. Per il Magazzino
class InventarioImport(BaseModel):
    materiale: str
    area_stanza: str 
    quantita: int = 0
    soglia_minima: int = 2
    obiettivo: int = 5

# --- ENDPOINT RAPIDI (+ e -) ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0:
            item.quantita -= 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

# --- PAZIENTI (INVARIATO) ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }
    column_list = [
        Paziente.cognome, Paziente.nome, Paziente.area,
        Paziente.visita_medica, Paziente.data_visita,
        Paziente.disdetto, Paziente.data_disdetta
    ]
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    form_columns = [
        Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note,
        Paziente.visita_medica, Paziente.data_visita, 
        Paziente.disdetto, Paziente.data_disdetta
    ]

    @action(name="segna_disdetto", label="❌ Segna come Disdetto", confirmation_message="Confermi?")
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

# --- MAGAZZINO (INVARIATO) ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"

    def formatta_con_bottoni(model, attribute):
        stato = ""
        if model.quantita <= model.soglia_minima:
            stato = f"🔴 {model.quantita} (ORDINA!)"
        elif model.quantita >= model.obiettivo:
            stato = f"🌟 {model.quantita} (Pieno)"
        else:
            stato = f"✅ {model.quantita} (Ok)"
            
        style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; margin:0 2px; background:#f9f9f9;"
        btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a>'
        btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">➕</a>'
        
        return Markup(f"{btn_meno} &nbsp; <b>{stato}</b> &nbsp; {btn_piu}")

    column_formatters = {
        Inventario.quantita: formatta_con_bottoni
    }

    column_list = [
        Inventario.materiale, 
        Inventario.area_stanza, 
        Inventario.quantita, 
        Inventario.soglia_minima, 
        Inventario.obiettivo
    ]
    
    form_columns = [
        Inventario.materiale,
        Inventario.area_stanza,
        Inventario.quantita,
        Inventario.soglia_minima,
        Inventario.obiettivo
    ]

# --- PRESTITI (VERSIONE POTENZIATA) ---
class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-stopwatch"

    # 1. FILTRO AUTOMATICO: Nasconde i restituiti
    def list_query(self, request):
        return select(Prestito).where(Prestito.restituito == False)

    # 2. CALCOLO SCADENZA VISIVA
    def formatta_scadenza(model, attribute):
        if not model.data_scadenza:
            return "⏳ In corso"
        
        oggi = date.today()
        giorni_mancanti = (model.data_scadenza - oggi).days

        if giorni_mancanti < 0:
            return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(giorni_mancanti)} gg!</span>')
        elif giorni_mancanti == 0:
            return Markup('<span style="color:orange; font-weight:bold;">🟠 SCADE OGGI!</span>')
        else:
            return Markup(f"⏳ Scade tra {giorni_mancanti} gg")

    column_formatters = {
        Prestito.data_scadenza: formatta_scadenza
    }

    column_list = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente, # Mostra nome e cognome
        Prestito.data_inizio,
        Prestito.data_scadenza
    ]

    form_columns = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente, # Menu a tendina
        Prestito.data_inizio,
        Prestito.durata_giorni,
        Prestito.restituito # Se lo spunti, sparisce dalla lista
    ]

    # 3. LOGICA CALCOLO DATA
    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni:
            model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

# --- ALTRE VISTE ---
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

# --- IMPORTATORI ---
@app.post("/import-rapido")
def import_pazienti(lista_pazienti: List[PazienteImport]):
    try:
        count = 0
        with Session(engine) as session:
            for p in lista_pazienti:
                nuovo = Paziente(nome=p.nome, cognome=p.cognome, area=p.area)
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} pazienti."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/import-magazzino")
def import_magazzino(lista_articoli: List[InventarioImport]):
    try:
        count = 0
        with Session(engine) as session:
            for item in lista_articoli:
                nuovo = Inventario(
                    materiale=item.materiale,
                    area_stanza=item.area_stanza,
                    quantita=item.quantita,
                    soglia_minima=item.soglia_minima,
                    obiettivo=item.obiettivo
                )
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} articoli in magazzino."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Completo e Funzionante"}
