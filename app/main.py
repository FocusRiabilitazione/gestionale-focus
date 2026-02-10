from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza, AreaMagazzino

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURA IMPORT ---
class PazienteImport(BaseModel):
    nome: str
    cognome: str
    area: str 

# --- ENDPOINT RAPIDI (I "Comandi Segreti" restano uguali) ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1
            session.add(item)
            session.commit()
    # Torna alla pagina precedente (così funziona su tutte le viste)
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

# --- FUNZIONE DI FORMATTAZIONE CONDIVISA ---
# La definiamo qui fuori così la usano tutte le 5 sezioni
def formatta_magazzino(model, attribute):
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


# --- CLASSE BASE MAGAZZINO (Lo stampino per tutte le sezioni) ---
class InventarioBase(ModelView):
    # Configurazioni comuni a tutti
    column_formatters = { Inventario.quantita: formatta_magazzino }
    
    # Nella lista specifica togliamo la colonna "Area" perché è ovvia (siamo già nella sezione giusta)
    column_list = [
        Inventario.materiale, 
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

# --- LE 5 SEZIONI SPECIFICHE ---

class MagazzinoMano(InventarioBase, model=Inventario):
    name = "Mano"
    name_plural = "Mano"
    category = "Magazzino" # <--- Questo crea la cartella!
    icon = "fa-solid fa-hand"
    
    def list_query(self, request):
        return select(Inventario).where(Inventario.area_stanza == AreaMagazzino.MANO)

class MagazzinoSegreteria(InventarioBase, model=Inventario):
    name = "Segreteria"
    name_plural = "Segreteria"
    category = "Magazzino"
    icon = "fa-solid fa-stapler"
    
    def list_query(self, request):
        return select(Inventario).where(Inventario.area_stanza == AreaMagazzino.SEGRETERIA)

class MagazzinoStanze(InventarioBase, model=Inventario):
    name = "Stanze"
    name_plural = "Stanze"
    category = "Magazzino"
    icon = "fa-solid fa-door-closed"
    
    def list_query(self, request):
        return select(Inventario).where(Inventario.area_stanza == AreaMagazzino.STANZE)

class MagazzinoMedicinali(InventarioBase, model=Inventario):
    name = "Medicinali"
    name_plural = "Medicinali"
    category = "Magazzino"
    icon = "fa-solid fa-pills"
    
    def list_query(self, request):
        return select(Inventario).where(Inventario.area_stanza == AreaMagazzino.MEDICINALI)

class MagazzinoPulizie(InventarioBase, model=Inventario):
    name = "Pulizie"
    name_plural = "Pulizie"
    category = "Magazzino"
    icon = "fa-solid fa-broom"
    
    def list_query(self, request):
        return select(Inventario).where(Inventario.area_stanza == AreaMagazzino.PULIZIE)

# --- PAZIENTI (Invariato) ---
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

# --- ALTRE VISTE ---
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

# Aggiungiamo le sezioni del magazzino (l'ordine qui decide l'ordine nel menu)
admin.add_view(MagazzinoMano)
admin.add_view(MagazzinoStanze)
admin.add_view(MagazzinoSegreteria)
admin.add_view(MagazzinoMedicinali)
admin.add_view(MagazzinoPulizie)

admin.add_view(PazienteAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()

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

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Magazzino Diviso"}
