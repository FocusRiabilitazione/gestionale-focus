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

# ================= CONFIGURAZIONE DATABASE =================
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="Gestionale Focus Rehab")

# ================= MODELLI DATI (DATABASE) =================

# --- CATEGORIE (ENUMS) ---
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

# --- 1. PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "paziente"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None
    
    # Relazioni
    preventivi: List["Preventivo"] = Relationship(back_populates="paziente_rel")
    prestiti: List["Prestito"] = Relationship(back_populates="paziente")

    def __str__(self):
        return f"{self.cognome} {self.nome}"

# --- 2. MAGAZZINO ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario"
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- 3. PRESTITI ---
class Prestito(SQLModel, table=True):
    __tablename__ = "prestito"
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="paziente.id")
    paziente: Optional[Paziente] = Relationship(back_populates="prestiti")
    
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

# --- 4. LISTINO PREZZI (TRATTAMENTI) ---
class Trattamento(SQLModel, table=True):
    __tablename__ = "trattamento"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    area: AreaTrattamento = Field(default=AreaTrattamento.ALTRO)
    prezzo_base: float = Field(default=0.0)

    def __str__(self):
        # Questo trucco ordina visivamente il menu a tendina: "[MANO] - Laser"
        return f"[{self.area.value.upper()}] - {self.nome} (€ {self.prezzo_base})"

# --- 5. PREVENTIVI ---
class Preventivo(SQLModel, table=True):
    __tablename__ = "preventivo"
    id: Optional[int] = Field(default=None, primary_key=True)
    data_creazione: date = Field(default_factory=date.today)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="paziente.id")
    paziente_rel: Optional[Paziente] = Relationship(back_populates="preventivi")

    descrizione: Optional[str] = Field(default=None, description="Note percorso")
    totale: float = Field(default=0.0)
    accettato: bool = False

    # Relazione righe (Cruciale per far apparire la tabella)
    righe: List["RigaPreventivo"] = Relationship(back_populates="preventivo")

    def __str__(self):
        return f"Prev. #{self.id} - {self.data_creazione}"

class RigaPreventivo(SQLModel, table=True):
    __tablename__ = "riga_preventivo"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    preventivo_id: Optional[int] = Field(default=None, foreign_key="preventivo.id")
    preventivo: Optional[Preventivo] = Relationship(back_populates="righe")
    
    trattamento_id: Optional[int] = Field(default=None, foreign_key="trattamento.id")
    trattamento: Optional[Trattamento] = Relationship()
    
    quantita: int = Field(default=1)
    sconto: float = Field(default=0.0)

# --- 6. SCADENZE ---
class Scadenza(SQLModel, table=True):
    __tablename__ = "scadenza"
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False

# ================= INTERFACCIA AMMINISTRATORE (SQLADMIN) =================

# --- 1. PAZIENTI VIEW ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"
    name_plural = "Pazienti"
    icon = "fa-solid fa-user-injured"
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]
    form_columns = [Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]
    column_formatters = {Paziente.disdetto: lambda m, a: "✅" if m.disdetto else ""}

# --- 2. MAGAZZINO VIEW (Versione Icone + Bottoni) ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"
    name_plural = "Magazzino"
    icon = "fa-solid fa-box"

    # Funzione visuale per le Aree (Emoji)
    def formatta_area(model, attribute):
        val = str(model.area_stanza).upper()
        if "MANO" in val: return "🖐️ MANO"
        if "MEDICINALI" in val: return "💊 MEDICINALI"
        if "PULIZIE" in val: return "🧹 PULIZIE"
        if "SEGRETERIA" in val: return "📎 SEGRETERIA"
        if "STANZE" in val: return "🚪 STANZE"
        return f"📦 {model.area_stanza}"

    # Funzione Bottoni + Semaforo
    def formatta_bottoni(model, attribute):
        q = model.quantita if model.quantita is not None else 0
        stato = ""
        if q <= model.soglia_minima: stato = f'<span style="color:red">🔴 <b>{q}</b></span>'
        elif q >= model.obiettivo: stato = f'<span style="color:green">🌟 <b>{q}</b></span>'
        else: stato = f'<span style="color:blue">✅ <b>{q}</b></span>'
        
        btn_style = "text-decoration:none; border:1px solid #ccc; padding:2px 8px; border-radius:4px; margin:0 5px; background:white; color:black;"
        return Markup(f'<a href="/magazzino/meno/{model.id}" style="{btn_style}">-</a> {stato} <a href="/magazzino/piu/{model.id}" style="{btn_style}">+</a>')

    column_formatters = {
        Inventario.area_stanza: formatta_area,
        Inventario.quantita: formatta_bottoni
    }
    
    column_list = [Inventario.area_stanza, Inventario.materiale, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    column_default_sort = "area_stanza" # Raggruppa per area automaticamente
    form_columns = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

# --- 3. PRESTITI VIEW ---
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

# --- 4. PREVENTIVI VIEW (Con Tabella Righe) ---
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    # Questa classe definisce la tabella dentro il preventivo
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]
    form_columns = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-invoice-dollar"

    # ATTIVAZIONE TABELLA INTERNA
    inlines = [RigaPreventivoInline]

    column_list = [Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.totale, Preventivo.accettato]
    form_columns = [Preventivo.paziente_rel, Preventivo.data_creazione, Preventivo.descrizione, Preventivo.accettato]

    # PULSANTI PROTOCOLLI RAPIDI
    @action(name="crea_schiena", label="➕ Protocollo Schiena", confirmation_message="Creo?")
    def action_schiena(self, request: Request): return self._crea_protocollo(request, "SCHIENA")
    
    @action(name="crea_ginocchio", label="➕ Protocollo Ginocchio", confirmation_message="Creo?")
    def action_ginocchio(self, request: Request): return self._crea_protocollo(request, "GINOCCHIO")

    def _crea_protocollo(self, request, tipo):
        # Definiamo qui i protocolli per semplicità
        PROTOCOLLI = {
            "SCHIENA": [{"nome": "Valutazione", "qty": 1}, {"nome": "Terapia Manuale", "qty": 5}, {"nome": "Tecar", "qty": 5}],
            "GINOCCHIO": [{"nome": "Valutazione", "qty": 1}, {"nome": "Rieducazione", "qty": 10}, {"nome": "Laser", "qty": 5}]
        }
        with self.session_maker() as session:
            p = Preventivo(descrizione=f"Protocollo {tipo}")
            session.add(p); session.commit(); session.refresh(p)
            for item in PROTOCOLLI.get(tipo, []):
                # Cerca un trattamento simile nel nome
                stmt = select(Trattamento).where(Trattamento.nome.contains(item["nome"]))
                t = session.exec(stmt).first()
                if t:
                    riga = RigaPreventivo(preventivo_id=p.id, trattamento_id=t.id, quantita=item["qty"])
                    session.add(riga)
            session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="preventivo"), status_code=303)

    # CALCOLO TOTALE AL SALVATAGGIO
    async def after_model_change(self, data, model, is_created, request):
        with Session(engine) as session:
            # Ricarica il modello con le righe aggiornate
            stmt = select(Preventivo).where(Preventivo.id == model.id)
            prev = session.exec(stmt).first()
            tot = 0
            if prev.righe:
                for riga in prev.righe:
                    if riga.trattamento:
                        tot += (riga.trattamento.prezzo_base * riga.quantita) - riga.sconto
            prev.totale = tot
            session.add(prev)
            session.commit()

# --- 5. SCADENZE VIEW ---
class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# ================= ATTIVAZIONE APP =================
admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
# admin.add_view(TrattamentoAdmin) # Nascosto volutamente
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup():
    init_db()

# ================= ENDPOINT MANUALI E IMPORTATORI =================

# Endpoint Magazzino Bottoni
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

# Importatori Massivi (JSON)
class TrattamentoImport(BaseModel):
    nome: str; area: str; prezzo: float

@app.post("/import-trattamenti")
def import_trattamenti(l: List[TrattamentoImport]):
    with Session(engine) as s:
        for i in l: s.add(Trattamento(nome=i.nome, area=i.area, prezzo_base=i.prezzo))
        s.commit()
    return {"msg": "Listino importato!"}

@app.get("/")
def home(): return {"msg": "Gestionale Focus Rehab - Stabile"}
