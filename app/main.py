from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

# Assicurati che models contenga tutte le classi nuove
from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza, Trattamento, RigaPreventivo

app = FastAPI(title="Gestionale Focus Rehab")

# --- STRUTTURE IMPORTAZIONE ---
class PazienteImport(BaseModel):
    nome: str; cognome: str; area: str
class InventarioImport(BaseModel):
    materiale: str; area_stanza: str; quantita: int=0; soglia_minima: int=2; obiettivo: int=5
class PrestitoImport(BaseModel):
    oggetto: str; area: str; nome_paziente: str; cognome_paziente: str; durata_giorni: int=7
class TrattamentoImport(BaseModel):
    nome: str; area: str; prezzo: float

# --- PROTOCOLLI RAPIDI ---
PROTOCOLLI = {
    "SCHIENA": [
        {"nome": "Valutazione", "qty": 1},
        {"nome": "Terapia Manuale", "qty": 5},
        {"nome": "Tecar", "qty": 5}
    ],
    "GINOCCHIO": [
        {"nome": "Valutazione", "qty": 1},
        {"nome": "Rieducazione", "qty": 10},
        {"nome": "Laser", "qty": 5}
    ]
}

# --- AZIONI RAPIDE ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0:
            item.quantita -= 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

# --- 1. PAZIENTI ---
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
    @action(name="segna_disdetto", label="❌ Segna Disdetto", confirmation_message="Confermi?")
    def action_disdetto(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        with self.session_maker() as session:
            for pk in pks:
                if pk.isdigit():
                    model = session.get(Paziente, int(pk))
                    if model: model.disdetto = True; model.data_disdetta = date.today(); session.add(model)
            session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="paziente"), status_code=303)

# --- 2. MAGAZZINO ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"

    def formatta_con_bottoni(model, attribute):
        stato = ""
        q = model.quantita if model.quantita is not None else 0
        s = model.soglia_minima if model.soglia_minima is not None else 0
        o = model.obiettivo if model.obiettivo is not None else 0

        if q <= s:
            stato = f"🔴 {q} (ORDINA!)"
        elif q >= o:
            stato = f"🌟 {q} (Pieno)"
        else:
            stato = f"✅ {q} (Ok)"
        style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; margin:0 2px; background:#f9f9f9;"
        btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a>'
        btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">➕</a>'
        return Markup(f"{btn_meno} &nbsp; <b>{stato}</b> &nbsp; {btn_piu}")

    column_formatters = {Inventario.quantita: formatta_con_bottoni}
    column_list = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    form_columns = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

# --- 3. PRESTITI ---
class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"
    name_plural = "Prestiti"
    icon = "fa-solid fa-stopwatch"
    def list_query(self, request): return select(Prestito).where(Prestito.restituito == False)
    def formatta_scadenza(model, attribute):
        if not model.data_scadenza: return "⏳ In corso"
        diff = (model.data_scadenza - date.today()).days
        if diff < 0: return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(diff)} gg!</span>')
        return Markup(f"⏳ Scade tra {diff} gg")
    column_formatters = {Prestito.data_scadenza: formatta_scadenza}
    column_list = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_scadenza]
    form_columns = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]
    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni: model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

# --- 4. LISTINO PREZZI (RIATTIVATO) ---
class TrattamentoAdmin(ModelView, model=Trattamento):
    name = "Listino Prezzi"
    name_plural = "Listino"
    icon = "fa-solid fa-tags"
    column_list = [Trattamento.area, Trattamento.nome, Trattamento.prezzo_base]
    form_columns = [Trattamento.nome, Trattamento.area, Trattamento.prezzo_base]

# --- 5. PREVENTIVI ---
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-invoice-dollar"
    inlines = [RigaPreventivoInline] # TABELLA INTERNA ATTIVA

    column_list = [Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.area_intervento, Preventivo.totale]
    
    # Qui scegli l'area solo come info, poi sotto aggiungi i trattamenti
    form_columns = [Preventivo.paziente_rel, Preventivo.area_intervento, Preventivo.data_creazione, Preventivo.descrizione, Preventivo.accettato]

    # CALCOLO TOTALE AL SALVATAGGIO
    async def after_model_change(self, data, model, is_created, request):
        # Ricalcolo preciso dopo il salvataggio
        with Session(engine) as session:
            # Ricarichiamo il preventivo con le righe
            stmt = select(Preventivo).where(Preventivo.id == model.id)
            prev = session.exec(stmt).first()
            if prev and prev.righe:
                tot = 0
                for riga in prev.righe:
                    if riga.trattamento:
                        tot += (riga.trattamento.prezzo_base * riga.quantita) - riga.sconto
                prev.totale = tot
                session.add(prev)
                session.commit()

    # BOTTONI RAPIDI
    @action(name="crea_schiena", label="➕ SCHIENA", confirmation_message="Creo?")
    def action_schiena(self, request: Request): return self._crea_protocollo(request, "SCHIENA")
    @action(name="crea_ginocchio", label="➕ GINOCCHIO", confirmation_message="Creo?")
    def action_ginocchio(self, request: Request): return self._crea_protocollo(request, "GINOCCHIO")

    def _crea_protocollo(self, request, tipo):
        with self.session_maker() as session:
            p = Preventivo(descrizione=f"Protocollo {tipo}")
            session.add(p); session.commit(); session.refresh(p)
            for item in PROTOCOLLI.get(tipo, []):
                stmt = select(Trattamento).where(Trattamento.nome.contains(item["nome"])) # Cerca simile
                t = session.exec(stmt).first()
                if t:
                    riga = RigaPreventivo(preventivo_id=p.id, trattamento_id=t.id, quantita=item["qty"])
                    session.add(riga)
            session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="preventivo"), status_code=303)

# --- 6. SCADENZE ---
class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# --- ATTIVAZIONE ---
admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(TrattamentoAdmin) # ORA È ATTIVO!
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup(): init_db()

# --- IMPORTATORI ---
@app.post("/import-rapido")
def import_pazienti(l: List[PazienteImport]):
    with Session(engine) as s:
        for p in l: s.add(Paziente(nome=p.nome, cognome=p.cognome, area=p.area))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-magazzino")
def import_magazzino(l: List[InventarioImport]):
    with Session(engine) as s:
        for i in l: s.add(Inventario(materiale=i.materiale, area_stanza=i.area_stanza, quantita=i.quantita, soglia_minima=i.soglia_minima, obiettivo=i.obiettivo))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-prestiti")
def import_prestiti(l: List[PrestitoImport]):
    with Session(engine) as s:
        for i in l:
            p = s.exec(select(Paziente).where(Paziente.nome==i.nome_paziente, Paziente.cognome==i.cognome_paziente)).first()
            s.add(Prestito(oggetto=i.oggetto, area=i.area, paziente_id=p.id if p else None, durata_giorni=i.durata_giorni))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-trattamenti")
def import_trattamenti(l: List[TrattamentoImport]):
    with Session(engine) as s:
        for i in l: s.add(Trattamento(nome=i.nome, area=i.area, prezzo_base=i.prezzo))
        s.commit()
    return {"msg": "Ok"}
