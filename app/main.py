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

# --- ENDPOINT RAPIDI (+ e -) ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1
            session.add(item)
            session.commit()
    # Torna alla pagina precedente
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

# --- FORMATTAZIONE VISIVA SICURA (Anticrash) ---

def formatta_area(model, attribute):
    # 1. Recuperiamo il valore in modo sicuro (gestisce sia Enum che stringhe)
    valore_grezzo = getattr(model, "area_stanza", "Altro")
    area = "Altro"
    
    if hasattr(valore_grezzo, "value"):
        area = valore_grezzo.value # È un Enum
    else:
        area = str(valore_grezzo) # È una stringa o altro
        
    # 2. Assegniamo i colori
    colore = "gray" 
    if area == "Mano": colore = "#3498db"        # Blu
    elif area == "Medicinali": colore = "#e74c3c" # Rosso
    elif area == "Pulizie": colore = "#f1c40f"    # Giallo
    elif area == "Segreteria": colore = "#9b59b6" # Viola
    elif area == "Stanze": colore = "#2ecc71"     # Verde
    
    # 3. Disegniamo l'etichetta
    html = f'<span style="background-color:{colore}; color:white; padding:4px 8px; border-radius:12px; font-size:0.85em; font-weight:bold;">{area}</span>'
    return Markup(html)

def formatta_quantita(model, attribute):
    # Controlli di sicurezza per evitare crash su valori None
    q = model.quantita if model.quantita is not None else 0
    soglia = model.soglia_minima if model.soglia_minima is not None else 0
    obiett = model.obiettivo if model.obiettivo is not None else 0
    
    stato = ""
    if q <= soglia:
        stato = f"🔴 {q} (ORDINA!)"
    elif q >= obiett:
        stato = f"🌟 {q} (Pieno)"
    else:
        stato = f"✅ {q} (Ok)"
        
    style = "text-decoration:none; border:1px solid #ccc; padding:2px 7px; border-radius:4px; margin:0 3px; background:#fff; font-weight:bold; color:#333;"
    btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">-</a>'
    btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">+</a>'
    
    return Markup(f"{btn_meno} {stato} {btn_piu}")


# --- MAGAZZINO ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Magazzino"
    name_plural = "Magazzino"
    icon = "fa-solid fa-boxes-stacked"
    
    column_formatters = {
        Inventario.quantita: formatta_quantita,
        Inventario.area_stanza: formatta_area
    }

    column_list = [
        Inventario.materiale, 
        Inventario.area_stanza, 
        Inventario.quantita, 
        Inventario.soglia_minima, 
        Inventario.obiettivo
    ]
    
    # ORDINAMENTO: Raggruppa tutto per area stanza automaticamente
    column_default_sort = "area_stanza" 
    
    column_searchable_list = [Inventario.materiale]
    column_filters = [Inventario.area_stanza]

    form_columns = [
        Inventario.materiale,
        Inventario.area_stanza,
        Inventario.quantita,
        Inventario.soglia_minima,
        Inventario.obiettivo
    ]

# --- PAZIENTI ---
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
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
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
    return {"msg": "Gestionale Focus Rehab - Riparato"}
