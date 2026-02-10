from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select, text
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup
from sqlalchemy import create_engine

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza

app = FastAPI(title="Gestionale Focus Rehab")

# ==========================================
# 1. STRUTTURE PER IMPORTAZIONE (JSON)
# ==========================================

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

class PrestitoImport(BaseModel):
    oggetto: str
    area: str
    nome_paziente: str
    cognome_paziente: str
    durata_giorni: int = 7


# ==========================================
# 2. ENDPOINT RAPIDI (MAGAZZINO + e -)
# ==========================================

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


# ==========================================
# 3. FUNZIONI DI FORMATTAZIONE GRAFICA
# ==========================================

# Questa funzione deve stare QUI FUORI per non rompere SQLAdmin
def formatta_con_bottoni(model, attribute):
    """Crea i bottoni + e - e il semaforo colorato"""
    stato = ""
    # Protezione se i dati sono nulli
    q = model.quantita if model.quantita is not None else 0
    soglia = model.soglia_minima if model.soglia_minima is not None else 0
    obiett = model.obiettivo if model.obiettivo is not None else 0

    if q <= soglia:
        stato = f"🔴 {q} (ORDINA!)"
    elif q >= obiett:
        stato = f"🌟 {q} (Pieno)"
    else:
        stato = f"✅ {q} (Ok)"
        
    style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; margin:0 2px; background:#f9f9f9;"
    btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a>'
    btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">➕</a>'
    
    return Markup(f"{btn_meno} &nbsp; <b>{stato}</b> &nbsp; {btn_piu}")

def formatta_scadenza(model, attribute):
    """Calcola i giorni mancanti per il prestito"""
    if not model.data_scadenza:
        return "⏳ In corso"
    
    oggi = date.today()
    diff = (model.data_scadenza - oggi).days

    if diff < 0:
        return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(diff)} gg!</span>')
    elif diff == 0:
        return Markup('<span style="color:orange; font-weight:bold;">🟠 SCADE OGGI!</span>')
    else:
        return Markup(f"⏳ Scade tra {diff} gg")


# ==========================================
# 4. CONFIGURAZIONE VISTE AMMINISTRATORE
# ==========================================

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
        Paziente.disdetto
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


class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"

    # Colleghiamo la funzione esterna qui
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


class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-stopwatch"

    # Nasconde gli oggetti restituiti dalla lista principale
    def list_query(self, request):
        return select(Prestito).where(Prestito.restituito == False)

    column_formatters = {
        Prestito.data_scadenza: formatta_scadenza
    }

    column_list = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente,
        Prestito.data_inizio,
        Prestito.data_scadenza
    ]

    form_columns = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente,
        Prestito.data_inizio,
        Prestito.durata_giorni,
        Prestito.restituito
    ]

    # Calcolo automatico data scadenza
    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni:
            model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)


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


# ==========================================
# 5. ATTIVAZIONE E REPAIR
# ==========================================

admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()
    
    # --- AUTO-REPAIR DATABASE ---
    # Questo pezzo controlla se il tuo database è vecchio e aggiunge
    # le colonne mancanti (soglia e obiettivo) SENZA cancellare nulla.
    with Session(engine) as session:
        try:
            session.exec(text("ALTER TABLE inventario_smart_v2 ADD COLUMN soglia_minima INTEGER DEFAULT 2"))
            session.commit()
        except Exception:
            pass # Colonna già esistente
            
        try:
            session.exec(text("ALTER TABLE inventario_smart_v2 ADD COLUMN obiettivo INTEGER DEFAULT 5"))
            session.commit()
        except Exception:
            pass # Colonna già esistente


# ==========================================
# 6. IMPORTATORI MASSIVI
# ==========================================

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
        return {"messaggio": f"Fatto! Importati {count} articoli."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/import-prestiti")
def import_prestiti(lista_prestiti: List[PrestitoImport]):
    try:
        count = 0
        with Session(engine) as session:
            for item in lista_prestiti:
                # Cerca il paziente
                stmt = select(Paziente).where(
                    Paziente.nome == item.nome_paziente, 
                    Paziente.cognome == item.cognome_paziente
                )
                paziente_trovato = session.exec(stmt).first()
                pid = paziente_trovato.id if paziente_trovato else None

                nuovo = Prestito(
                    oggetto=item.oggetto,
                    area=item.area,
                    paziente_id=pid,
                    durata_giorni=item.durata_giorni,
                    data_inizio=date.today(),
                    data_scadenza=date.today() + timedelta(days=item.durata_giorni)
                )
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} prestiti."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Versione Full Funzionante"}
