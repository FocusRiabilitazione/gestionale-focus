from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta # <--- Importante per calcolare i giorni
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURE IMPORT ---
class PazienteImport(BaseModel):
    nome: str
    cognome: str
    area: str 

class InventarioImport(BaseModel):
    materiale: str
    area_stanza: str
    quantita: int = 0
    soglia_minima: int = 2
    obiettivo: int = 5

# --- ENDPOINT RAPIDI ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.headers.get("referer"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0:
            item.quantita -= 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.headers.get("referer"), status_code=303)

# --- FORMATTAZIONE VISIVA ---
def formatta_stato_prestito(model, attribute):
    if model.restituito:
        return Markup("✅ <b>RESTITUITO</b>")
    
    oggi = date.today()
    
    # Se non c'è data scadenza (caso raro), gestiamo l'errore
    if not model.data_scadenza:
        return "⏳ In corso"

    giorni_mancanti = (model.data_scadenza - oggi).days

    if giorni_mancanti < 0:
        return Markup(f"🔴 <b>SCADUTO da {abs(giorni_mancanti)} gg!</b>")
    elif giorni_mancanti == 0:
        return Markup("🟠 <b>SCADE OGGI!</b>")
    else:
        return Markup(f"⏳ Scade tra {giorni_mancanti} gg")

# --- ADMIN SECTIONS ---

class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    form_columns = [Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]

class InventarioAdmin(ModelView, model=Inventario):
    name = "Magazzino"
    name_plural = "Magazzino"
    icon = "fa-solid fa-boxes-stacked"
    
    def formatta_con_bottoni(model, attribute):
        stato = ""
        q = model.quantita if model.quantita is not None else 0
        soglia = model.soglia_minima if model.soglia_minima is not None else 0
        obiett = model.obiettivo if model.obiettivo is not None else 0
        if q <= soglia: stato = f"🔴 {q} (ORDINA!)"
        elif q >= obiett: stato = f"🌟 {q} (Pieno)"
        else: stato = f"✅ {q} (Ok)"
        style = "text-decoration:none; border:1px solid #ccc; padding:2px 7px; border-radius:4px; margin:0 3px; background:#fff; font-weight:bold; color:#333;"
        return Markup(f'<a href="/magazzino/meno/{model.id}" style="{style}">-</a> {stato} <a href="/magazzino/piu/{model.id}" style="{style}">+</a>')

    column_formatters = {Inventario.quantita: formatta_con_bottoni}
    column_list = [Inventario.area_stanza, Inventario.materiale, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    column_default_sort = "area_stanza" 
    column_searchable_list = [Inventario.materiale]
    column_filters = [Inventario.area_stanza]
    form_columns = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

# --- PRESTITI (NUOVA SEZIONE) ---
class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-stopwatch" # Icona orologio

    column_formatters = {
        Prestito.data_scadenza: formatta_stato_prestito
    }

    column_list = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente, # Qui apparirà il nome grazie alla relazione
        Prestito.data_inizio,
        Prestito.durata_giorni,
        Prestito.data_scadenza,
        Prestito.restituito
    ]

    # ORDINAMENTO AUTOMATICO
    # Vediamo prima i prestiti scaduti o vicini alla scadenza
    column_default_sort = [("restituito", False), ("data_scadenza", False)]

    # Quando crei/modifichi un prestito
    form_columns = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente, # Questo crea il MENU A TENDINA AUTOMATICO!
        Prestito.data_inizio,
        Prestito.durata_giorni,
        Prestito.restituito
    ]

    # MAGIA: CALCOLO AUTOMATICO SCADENZA
    async def on_model_change(self, data, model, is_created, request):
        # Se c'è una data inizio e una durata, calcoliamo la scadenza
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
                nuovo = Inventario(materiale=item.materiale, area_stanza=item.area_stanza, quantita=item.quantita, soglia_minima=item.soglia_minima, obiettivo=item.obiettivo)
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} articoli."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Prestiti Intelligenti"}
