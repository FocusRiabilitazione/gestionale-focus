from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, Field, Relationship, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from markupsafe import Markup
from enum import Enum
from sqlalchemy import create_engine

# --- DATABASE SETUP ---
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="Gestionale Focus Rehab")

# ================= MODELLI (DATABASE) =================

# ENUMS
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

class AreaPrestito(str, Enum):
    OGGETTI = "Oggetti"
    ELETTROMEDICALI = "Elettromedicali"

class AreaTrattamento(str, Enum):
    MANO = "Mano"
    COLONNA = "Colonna"
    GINOCCHIO = "Ginocchio"
    SPALLA = "Spalla"
    VISITA = "Visita"
    ALTRO = "Altro"

# 1. PAZIENTI
class Paziente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None
    
    preventivi: List["Preventivo"] = Relationship(back_populates="paziente_rel")

    def __str__(self):
        return f"{self.cognome} {self.nome}"

# 2. MAGAZZINO
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# 3. PRESTITI
class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    paziente_id: Optional[int] = Field(default=None, foreign_key="paziente.id")
    paziente: Optional[Paziente] = Relationship()
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

# 4. LISTINO PREZZI (Trattamenti)
class Trattamento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    area: AreaTrattamento = Field(default=AreaTrattamento.ALTRO)
    prezzo_base: float = Field(default=0.0)

    def __str__(self):
        # Questo fa apparire l'area nel menu a tendina: "[MANO] Laser"
        return f"[{self.area.value}] {self.nome} (€ {self.prezzo_base})"

# 5. PREVENTIVI
class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    data_creazione: date = Field(default_factory=date.today)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="paziente.id")
    paziente_rel: Optional[Paziente] = Relationship(back_populates="preventivi")

    descrizione: Optional[str] = Field(default=None, description="Note sul percorso")
    accettato: bool = False

    # Relazione con le righe
    righe: List["RigaPreventivo"] = Relationship(back_populates="preventivo")

    def __str__(self):
        return f"Prev. {self.id} ({self.data_creazione})"

class RigaPreventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    preventivo_id: Optional[int] = Field(default=None, foreign_key="preventivo.id")
    preventivo: Optional[Preventivo] = Relationship(back_populates="righe")
    
    trattamento_id: Optional[int] = Field(default=None, foreign_key="trattamento.id")
    trattamento: Optional[Trattamento] = Relationship()
    
    quantita: int = Field(default=1)
    sconto: float = Field(default=0.0)

# 6. SCADENZARIO
class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False

# ================= LOGICA ADMIN =================

# IMPORT MODELS
class PazienteImport(BaseModel):
    nome: str; cognome: str; area: str
class InventarioImport(BaseModel):
    materiale: str; area_stanza: str; quantita: int=0; soglia_minima: int=2; obiettivo: int=5
class PrestitoImport(BaseModel):
    oggetto: str; area: str; nome_paziente: str; cognome_paziente: str; durata_giorni: int=7
class TrattamentoImport(BaseModel):
    nome: str; area: str; prezzo: float

# --- 1. PAZIENTI ADMIN ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto]
    form_columns = [Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]
    
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }

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

# --- 2. MAGAZZINO ADMIN (VERSIONE STABILE) ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"

    def formatta_con_bottoni(model, attribute):
        stato = ""
        q = model.quantita if model.quantita is not None else 0
        if q <= model.soglia_minima: stato = f"🔴 {q} (ORDINA!)"
        elif q >= model.obiettivo: stato = f"🌟 {q} (Pieno)"
        else: stato = f"✅ {q} (Ok)"
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

# --- 3. PRESTITI ADMIN ---
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
        if model.data_inizio and model.durata_giorni:
            model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

# --- 4. PREVENTIVI ADMIN (Riparato) ---
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    # Questa è la tabellina interna
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]
    form_columns = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-invoice-dollar"

    # Attiviamo la tabella interna in modo sicuro
    inlines = [RigaPreventivoInline]

    column_list = [Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.accettato]
    
    # Rimosso il calcolo totale complesso per evitare crash. 
    # Ora salva semplicemente le righe.
    form_columns = [
        Preventivo.paziente_rel, 
        Preventivo.data_creazione, 
        Preventivo.descrizione, 
        Preventivo.accettato
    ]

# --- 5. SCADENZE ADMIN ---
class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]


# --- ATTIVAZIONE ---
admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
# Nota: Non aggiungiamo TrattamentoAdmin così resta nascosto, ma il DB lo usa.
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()

# --- IMPORTATORI (Endpoints) ---
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

# Endpoint manuali per Magazzino
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item: item.quantita += 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0: item.quantita -= 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/")
def home(): return {"msg": "Gestionale Focus Rehab - Stabile"}
