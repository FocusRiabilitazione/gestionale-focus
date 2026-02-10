from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

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
    # Torna alla pagina precedente mantenendo la posizione
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

# --- FORMATTAZIONE VISIVA SICURA (Emoji System) ---

def formatta_area_icona(model, attribute):
    # Trasformiamo tutto in stringa per sicurezza assoluta (anti-crash)
    valore = str(model.area_stanza).upper()
    
    # Assegnazione icone in base al testo contenuto
    icona = "📦" # Default
    nome_pulito = "Generico"

    if "MANO" in valore:
        icona = "🖐️"
        nome_pulito = "MANO"
    elif "MEDICINALI" in valore:
        icona = "💊"
        nome_pulito = "MEDICINALI"
    elif "PULIZIE" in valore:
        icona = "🧹"
        nome_pulito = "PULIZIE"
    elif "SEGRETERIA" in valore:
        icona = "📎"
        nome_pulito = "SEGRETERIA"
    elif "STANZE" in valore:
        icona = "🚪"
        nome_pulito = "STANZE"

    # Restituisce testo semplice + icona. Impossibile che si rompa.
    return f"{icona} {nome_pulito}"

def formatta_quantita_bottoni(model, attribute):
    q = model.quantita if model.quantita is not None else 0
    soglia = model.soglia_minima if model.soglia_minima is not None else 0
    obiett = model.obiettivo if model.obiettivo is not None else 0

    # Semaforo Emoji
    stato = ""
    if q <= soglia:
        stato = f"🔴 <b>{q}</b> (Ordina!)"
    elif q >= obiett:
        stato = f"🌟 <b>{q}</b> (Pieno)"
    else:
        stato = f"✅ <b>{q}</b> (Ok)"
        
    # Stile minimale per i bottoni
    style = "text-decoration:none; display:inline-block; border:1px solid #ccc; width:25px; text-align:center; border-radius:4px; margin:0 5px; background:white; color:black;"
    
    btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">-</a>'
    btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">+</a>'
    
    return Markup(f"{btn_meno} {stato} {btn_piu}")


# --- CONFIGURAZIONE PAZIENTI ---
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


# --- CONFIGURAZIONE MAGAZZINO ORDINATA ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Magazzino"
    name_plural = "Magazzino"
    icon = "fa-solid fa-boxes-stacked"

    # Rinominiamo le colonne per pulizia
    column_labels = {
        Inventario.area_stanza: "Reparto",
        Inventario.materiale: "Articolo",
        Inventario.quantita: "Giacenza Rapida",
        Inventario.soglia_minima: "Soglia",
        Inventario.obiettivo: "Target"
    }

    # Applichiamo le formattazioni sicure
    column_formatters = {
        Inventario.area_stanza: formatta_area_icona,
        Inventario.quantita: formatta_quantita_bottoni
    }

    # Ordine visivo: PRIMA il Reparto, POI l'Articolo
    column_list = [
        Inventario.area_stanza, 
        Inventario.materiale, 
        Inventario.quantita, 
        Inventario.soglia_minima, 
        Inventario.obiettivo
    ]
    
    # ⚠️ FONDAMENTALE: Ordina per Reparto.
    # Questo raggruppa visivamente le righe (tutte le mani insieme, tutte le stanze insieme).
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
    return {"msg": "Gestionale Focus Rehab - Magazzino Ordinato"}
