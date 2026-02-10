from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup
from enum import Enum

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

# --- FORMATTAZIONE GRAFICA (Semaforo + Badge Area) ---

# 1. BADGE AREA (BLINDATO ANTI-CRASH) 🛡️
def formatta_area_badge(model, attribute):
    try:
        # Tenta di recuperare il valore, gestendo sia Enum che stringhe
        raw_val = getattr(model, "area_stanza", "Altro")
        nome_area = "Altro"
        
        # Se è un Enum (come dovrebbe essere), prendiamo il .value
        if hasattr(raw_val, "value"):
            nome_area = raw_val.value
        else:
            nome_area = str(raw_val)
            
        # Assegnazione Colori
        colors = {
            "Mano": "#3498db",        # Blu
            "Medicinali": "#e74c3c",  # Rosso
            "Pulizie": "#f1c40f",     # Giallo
            "Segreteria": "#9b59b6",  # Viola
            "Stanze": "#2ecc71"       # Verde
        }
        colore = colors.get(nome_area, "#95a5a6") # Grigio default
        
        # HTML del Badge
        html = f'''
            <span style="
                background-color:{colore}; 
                color:white; 
                padding:4px 12px; 
                border-radius:12px; 
                font-size:0.85em; 
                font-weight:bold;
                display:inline-block;
                min-width: 90px;
                text-align:center;
                box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
            ">
                {nome_area}
            </span>
        '''
        return Markup(html)
    except:
        return Markup("<span>Errore Visivo</span>")

# 2. QUANTITÀ CON BOTTONI (Funzionante)
def formatta_con_bottoni(model, attribute):
    stato = ""
    q = model.quantita if model.quantita is not None else 0
    soglia = model.soglia_minima if model.soglia_minima is not None else 0
    obiett = model.obiettivo if model.obiettivo is not None else 0

    if q <= soglia:
        stato = f'<span style="color:#c0392b">🔴 {q}</span>' # Rosso scuro
    elif q >= obiett:
        stato = f'<span style="color:#27ae60">🌟 {q}</span>' # Verde scuro
    else:
        stato = f'<span style="color:#2980b9">✅ {q}</span>' # Blu scuro
        
    style = "text-decoration:none; border:1px solid #ddd; padding:2px 8px; border-radius:4px; margin:0 6px; background:#f8f9fa; font-weight:bold; color:#333;"
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


# --- CONFIGURAZIONE MAGAZZINO UNICO ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Magazzino"
    name_plural = "Magazzino"
    icon = "fa-solid fa-boxes-stacked" # L'icona tornerà visibile qui!

    # Etichette brevi per risparmiare spazio
    column_labels = {
        Inventario.area_stanza: "Reparto",
        Inventario.materiale: "Articolo",
        Inventario.quantita: "Giacenza",
        Inventario.soglia_minima: "Min",
        Inventario.obiettivo: "Target"
    }

    # Applichiamo le formattazioni (Colori e Bottoni)
    column_formatters = {
        Inventario.quantita: formatta_con_bottoni,
        Inventario.area_stanza: formatta_area_badge
    }

    # Ordine colonne: Il Reparto è il primo a sinistra
    column_list = [
        Inventario.area_stanza, 
        Inventario.materiale, 
        Inventario.quantita, 
        Inventario.soglia_minima, 
        Inventario.obiettivo
    ]
    
    # RAGGRUPPAMENTO AUTOMATICO
    # Questo è fondamentale: ordina la lista per reparto.
    # Così vedrai prima tutto il blocco 'Mano', poi tutto 'Medicinali', ecc.
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
admin.add_view(InventarioAdmin) # Solo una voce, pulita
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
    return {"msg": "Gestionale Focus Rehab - Magazzino Pulito e Colorato"}
