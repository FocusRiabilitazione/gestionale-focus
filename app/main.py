from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza, Trattamento, RigaPreventivo

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURE PER IMPORTAZIONE MASSIVA ---
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

class TrattamentoImport(BaseModel):
    nome: str
    area: str
    prezzo: float

# --- PROTOCOLLI RAPIDI (PREVENTIVI PRECOMPILATI) ---
PROTOCOLLI = {
    "SCHIENA": [
        {"nome": "Valutazione Funzionale", "qty": 1, "prezzo": 60},
        {"nome": "Terapia Manuale", "qty": 5, "prezzo": 50},
        {"nome": "Rieducazione Posturale", "qty": 5, "prezzo": 45}
    ],
    "SPALLA": [
        {"nome": "Valutazione", "qty": 1, "prezzo": 60},
        {"nome": "Laser Yag", "qty": 3, "prezzo": 35},
        {"nome": "Rieducazione Motoria", "qty": 10, "prezzo": 50}
    ],
    "GINOCCHIO": [
        {"nome": "Valutazione", "qty": 1, "prezzo": 60},
        {"nome": "Tecar Terapia", "qty": 5, "prezzo": 40},
        {"nome": "Rinforzo Muscolare", "qty": 10, "prezzo": 40}
    ]
}

# --- ENDPOINT RAPIDI (+ e - MAGAZZINO) ---
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


# --- AMMINISTRAZIONE ---

# 1. PAZIENTI
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto]
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    form_columns = [Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]

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

# 2. MAGAZZINO (LOGICA STABILE)
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

    column_formatters = {Inventario.quantita: formatta_con_bottoni}
    column_list = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    column_default_sort = "area_stanza" 
    column_searchable_list = [Inventario.materiale]
    column_filters = [Inventario.area_stanza]
    form_columns = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

# 3. PRESTITI
class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-stopwatch"

    def list_query(self, request):
        return select(Prestito).where(Prestito.restituito == False)

    def formatta_scadenza(model, attribute):
        if not model.data_scadenza: return "⏳ In corso"
        oggi = date.today()
        giorni_mancanti = (model.data_scadenza - oggi).days
        if giorni_mancanti < 0: return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(giorni_mancanti)} gg!</span>')
        elif giorni_mancanti == 0: return Markup('<span style="color:orange; font-weight:bold;">🟠 SCADE OGGI!</span>')
        else: return Markup(f"⏳ Scade tra {giorni_mancanti} gg")

    column_formatters = {Prestito.data_scadenza: formatta_scadenza}
    column_list = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_scadenza]
    form_columns = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]

    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni:
            model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

# 4. LISTINO PREZZI
class TrattamentoAdmin(ModelView, model=Trattamento):
    name = "Listino Prezzi"
    name_plural = "Listino Prezzi"
    icon = "fa-solid fa-tags"
    column_list = [Trattamento.area, Trattamento.nome, Trattamento.prezzo_base]
    form_columns = [Trattamento.nome, Trattamento.area, Trattamento.prezzo_base]

# 5. PREVENTIVI (Nuova Configurazione Avanzata)
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    # Tabellina interna al preventivo
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto_unitario]
    form_columns = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto_unitario]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-signature"

    # Attiva la modifica delle righe direttamente dentro il preventivo
    inlines = [RigaPreventivoInline]

    column_list = [Preventivo.id, Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.totale_calcolato, Preventivo.accettato]
    
    # Campi del form, inclusi quelli descrittivi e per le rate
    form_columns = [
        Preventivo.paziente_rel,
        Preventivo.data_creazione,
        Preventivo.descrizione_percorso, 
        Preventivo.note_pagamento,
        Preventivo.accettato
    ]

    # --- AZIONI RAPIDE (PROTOCOLLI) ---
    @action(name="crea_schiena", label="➕ Protocollo Schiena", confirmation_message="Creo preventivo SCHIENA?")
    def action_schiena(self, request: Request): return self._crea_da_protocollo(request, "SCHIENA")

    @action(name="crea_spalla", label="➕ Protocollo Spalla", confirmation_message="Creo preventivo SPALLA?")
    def action_spalla(self, request: Request): return self._crea_da_protocollo(request, "SPALLA")

    @action(name="crea_ginocchio", label="➕ Protocollo Ginocchio", confirmation_message="Creo preventivo GINOCCHIO?")
    def action_ginocchio(self, request: Request): return self._crea_da_protocollo(request, "GINOCCHIO")

    def _crea_da_protocollo(self, request, tipo):
        with self.session_maker() as session:
            # 1. Crea Testata
            prev = Preventivo(descrizione_percorso=f"Percorso Riabilitativo Completo - {tipo}", note_pagamento="Acconto 30% avvio cura, saldo fine ciclo.")
            session.add(prev); session.commit(); session.refresh(prev)
            
            # 2. Aggiunge Righe
            items = PROTOCOLLI.get(tipo, [])
            totale = 0
            for item in items:
                # Cerca o crea il trattamento al volo
                stmt = select(Trattamento).where(Trattamento.nome == item["nome"])
                tratt = session.exec(stmt).first()
                if not tratt:
                    tratt = Trattamento(nome=item["nome"], prezzo_base=item["prezzo"])
                    session.add(tratt); session.commit()
                
                # Aggiungi riga
                riga = RigaPreventivo(preventivo_id=prev.id, trattamento_id=tratt.id, quantita=item["qty"], prezzo_applicato=tratt.prezzo_base)
                session.add(riga)
                totale += (tratt.prezzo_base * item["qty"])
            
            prev.totale_calcolato = totale
            session.add(prev); session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="preventivo"), status_code=303)


# --- ALTRE VISTE ---
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
admin.add_view(TrattamentoAdmin) # Nuovo
admin.add_view(PreventivoAdmin)  # Nuovo
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()

# --- IMPORTATORI (TUTTI GLI ENDPOINT) ---
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

@app.post("/import-prestiti")
def import_prestiti(lista_prestiti: List[PrestitoImport]):
    try:
        count = 0
        with Session(engine) as session:
            for item in lista_prestiti:
                stmt = select(Paziente).where(Paziente.nome == item.nome_paziente, Paziente.cognome == item.cognome_paziente)
                paziente_trovato = session.exec(stmt).first()
                pid = paziente_trovato.id if paziente_trovato else None
                nuovo = Prestito(oggetto=item.oggetto, area=item.area, paziente_id=pid, durata_giorni=item.durata_giorni, data_inizio=date.today(), data_scadenza=date.today() + timedelta(days=item.durata_giorni))
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} prestiti."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/import-trattamenti")
def import_trattamenti(lista_trattamenti: List[TrattamentoImport]):
    try:
        count = 0
        with Session(engine) as session:
            for item in lista_trattamenti:
                nuovo = Trattamento(nome=item.nome, area=item.area, prezzo_base=item.prezzo)
                session.add(nuovo)
                count += 1
            session.commit()
        return {"messaggio": f"Fatto! Importati {count} trattamenti."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"msg": "Gestionale Focus Rehab - Preventivi Avanzati Attivi"}
