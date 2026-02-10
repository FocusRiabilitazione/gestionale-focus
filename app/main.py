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

# --- FUNZIONI DI FORMATTAZIONE GRAFICA ---

# 1. BADGE AREA (Versione Sicura Anti-Crash)
def formatta_area_badge(model, attribute):
    # Recuperiamo il valore gestendo sia il caso "Oggetto Enum" che "Stringa semplice"
    valore_grezzo = getattr(model, "area_stanza", "Altro")
    nome_area = str(valore_grezzo.value) if hasattr(valore_grezzo, "value") else str(valore_grezzo)
    
    # Colori pastello professionali
    colors = {
        "Mano": "#3498db",        # Blu
        "Medicinali": "#e74c3c",  # Rosso
        "Pulizie": "#f1c40f",     # Giallo
        "Segreteria": "#9b59b6",  # Viola
        "Stanze": "#2ecc71"       # Verde
    }
    colore = colors.get(nome_area, "#95a5a6") # Grigio se non trova il colore
    
    # Creiamo il badge HTML
    html = f'''
        <span style="
            background-color:{colore}; 
            color:white; 
            padding:4px 10px; 
            border-radius:15px; 
            font-size:0.85em; 
            font-weight:600;
            display:inline-block;
            min-width: 80px;
            text-align:center;
        ">
            {nome_area}
        </span>
    '''
    return Markup(html)

# 2. QUANTITÀ CON BOTTONI (La tua versione funzionante)
def formatta_con_bottoni(model, attribute):
    stato = ""
    if model.quantita <= model.soglia_minima:
        stato = f'<span style="color:#c0392b">🔴 {model.quantita} (ORDINA!)</span>'
    elif model.quantita >= model.obiettivo:
        stato = f'<span style="color:#27ae60">🌟 {model.quantita} (Pieno)</span>'
    else:
        stato = f'<span style="color:#2980b9">✅ {model.quantita} (Ok)</span>'
        
    style = "text-decoration:none; border:1px solid #ddd; padding:2px 8px; border-radius:4px; margin:0 5px; background:#fff; font-weight:bold; color:#555;"
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


# --- CONFIGURAZIONE MAGAZZINO PULITO ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Magazzino"
    name_plural = "Magazzino"
    icon = "fa-solid fa-boxes-stacked"

    # 1. Rinominiamo le colonne per renderle più corte e leggibili
    column_labels = {
        Inventario.area_stanza: "Reparto",
        Inventario.materiale: "Prodotto",
        Inventario.quantita: "Giacenza",
        Inventario.soglia_minima: "Min",
        Inventario.obiettivo: "Target"
    }

    # 2. Applichiamo le formattazioni grafiche
    column_formatters = {
        Inventario.quantita: formatta_con_bottoni,
        Inventario.area_stanza: formatta_area_badge
    }

    # 3. Ordine delle colonne: Prima il Reparto, poi il Prodotto
    column_list = [
        Inventario.area_stanza, 
        Inventario.materiale, 
        Inventario.quantita, 
        Inventario.soglia_minima, 
        Inventario.obiettivo
    ]
    
    # 4. TRUCCO ESSENZIALE: Ordina automaticamente per Reparto!
    # Questo raggruppa visivamente le righe senza bisogno di menu separati.
    column_default_sort = "area_stanza" 

    column_searchable_list = [Inventario.materiale]
    column_filters = [Inventario.area_stanza] # Aggiunge il filtro laterale
    
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
    return {"msg": "Gestionale Focus Rehab - Grafica Pulita"}
