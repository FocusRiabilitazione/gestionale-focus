from fastapi import FastAPI, Request, HTTPException
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select, Field, Relationship, text
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from markupsafe import Markup
from enum import Enum
from sqlalchemy import create_engine

# --- SETUP DATABASE ---
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

app = FastAPI(title="Gestionale Focus Rehab - Auto Repair")

# ================= MODELLI =================

class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

class AreaPrestito(str, Enum):
    OGGETTI = "Oggetti"
    ELETTROMEDICALI = "Elettromedicali"

class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_visite_v2"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None
    def __str__(self): return f"{self.cognome} {self.nome}"

class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_smart_v2"
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2) # Nuova colonna
    obiettivo: int = Field(default=5)     # Nuova colonna

class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_smart_v1"
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_visite_v2.id")
    paziente: Optional[Paziente] = Relationship()
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    totale: float
    data_creazione: date = Field(default_factory=date.today)

class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False

# ================= FUNZIONI DI RIPARAZIONE E AVVIO =================

def init_db():
    SQLModel.metadata.create_all(engine)

@app.on_event("startup")
def on_startup():
    # 1. Crea le tabelle se non esistono
    init_db()
    
    # 2. MECCANICO AUTOMATICO: Tenta di aggiungere le colonne mancanti
    # Se le colonne esistono già, ignora l'errore e prosegue.
    with Session(engine) as session:
        try:
            print("🔧 Tentativo riparazione Magazzino...")
            session.exec(text("ALTER TABLE inventario_smart_v2 ADD COLUMN soglia_minima INTEGER DEFAULT 2"))
            session.commit()
            print("✅ Colonna soglia_minima aggiunta!")
        except Exception:
            pass # Esiste già, tutto ok

        try:
            session.exec(text("ALTER TABLE inventario_smart_v2 ADD COLUMN obiettivo INTEGER DEFAULT 5"))
            session.commit()
            print("✅ Colonna obiettivo aggiunta!")
        except Exception:
            pass # Esiste già, tutto ok

# ================= ADMIN & LOGICA =================

# Importatori
class PazienteImport(BaseModel):
    nome: str; cognome: str; area: str
class InventarioImport(BaseModel):
    materiale: str; area_stanza: str; quantita: int=0; soglia_minima: int=2; obiettivo: int=5
class PrestitoImport(BaseModel):
    oggetto: str; area: str; nome_paziente: str; cognome_paziente: str; durata_giorni: int=7

# Endpoint Magazzino
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

# Formattatori
def formatta_con_bottoni(model, attribute):
    q = model.quantita if model.quantita is not None else 0
    s = model.soglia_minima if model.soglia_minima is not None else 0
    o = model.obiettivo if model.obiettivo is not None else 0
    if q <= s: stato = f"🔴 {q} (ORDINA!)"
    elif q >= o: stato = f"🌟 {q} (Pieno)"
    else: stato = f"✅ {q} (Ok)"
    style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; margin:0 2px; background:#f9f9f9;"
    return Markup(f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a> <b>{stato}</b> <a href="/magazzino/piu/{model.id}" style="{style}">➕</a>')

def formatta_scadenza(model, attribute):
    if not model.data_scadenza: return "⏳ In corso"
    diff = (model.data_scadenza - date.today()).days
    if diff < 0: return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(diff)} gg!</span>')
    return Markup(f"⏳ Scade tra {diff} gg")

# Viste Admin
class PazienteAdmin(ModelView, model=Paziente):
    name="Paziente"; name_plural="Pazienti"; icon="fa-solid fa-user-injured"
    column_formatters={Paziente.disdetto: lambda m,a: "✅" if m.disdetto else ""}
    column_list=[Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]
    form_columns=[Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]
    @action(name="segna_disdetto", label="❌ Segna Disdetto", confirmation_message="Confermi?")
    def action_disdetto(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        with self.session_maker() as session:
            for pk in pks:
                if pk.isdigit():
                    m = session.get(Paziente, int(pk))
                    if m: m.disdetto=True; m.data_disdetta=date.today(); session.add(m)
            session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="paziente"), status_code=303)

class InventarioAdmin(ModelView, model=Inventario):
    name="Articolo"; name_plural="Magazzino"; icon="fa-solid fa-box"
    column_formatters={Inventario.quantita: formatta_con_bottoni}
    column_list=[Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    column_default_sort="area_stanza"
    column_filters=[Inventario.area_stanza]
    form_columns=[Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

class PrestitoAdmin(ModelView, model=Prestito):
    name="Prestito"; name_plural="Prestiti"; icon="fa-solid fa-stopwatch"
    def list_query(self, request): return select(Prestito).where(Prestito.restituito == False)
    column_formatters={Prestito.data_scadenza: formatta_scadenza}
    column_list=[Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_scadenza]
    form_columns=[Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]
    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni: model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

class PreventivoAdmin(ModelView, model=Preventivo):
    name="Preventivo"; name_plural="Preventivi"; icon="fa-solid fa-file-invoice-dollar"
    column_list=[Preventivo.data_creazione, Preventivo.paziente, Preventivo.totale]

class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# Attivazione
admin = Admin(app, engine)
admin.add_view(PazienteAdmin); admin.add_view(InventarioAdmin); admin.add_view(PrestitoAdmin); admin.add_view(PreventivoAdmin); admin.add_view(ScadenzaAdmin)

# Endpoints Importazione
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
            s.add(Prestito(oggetto=i.oggetto, area=i.area, paziente_id=p.id if p else None, durata_giorni=i.durata_giorni, data_scadenza=date.today()+timedelta(days=i.durata_giorni)))
        s.commit()
    return {"msg": "Ok"}

@app.get("/")
def home(): return {"msg": "Gestionale Focus Rehab - Riparato"}
