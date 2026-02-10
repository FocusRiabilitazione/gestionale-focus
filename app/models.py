from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

# --- ENUMS (Categorie) ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

class AreaPrestito(str, Enum):
    OGGETTI = "Oggetti"
    ELETTROMEDICALI = "Elettromedicali"

class AreaTrattamento(str, Enum):
    RIABILITAZIONE = "Riabilitazione"
    TERAPIA_FISICA = "Terapia Fisica"
    VISITA = "Visita"
    ALTRO = "Altro"

# --- 1. PAZIENTI (INTATTO) ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_v5_stampa"
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

# --- 2. MAGAZZINO (INTATTO) ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_v5_stampa"
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- 3. PRESTITI (INTATTO) ---
class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_v5_stampa"
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_v5_stampa.id")
    paziente: Optional[Paziente] = Relationship(back_populates="prestiti")
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

# --- 4. LISTINO PREZZI (IL CERVELLO) ---
class Trattamento(SQLModel, table=True):
    __tablename__ = "listino_v5_stampa"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    area: AreaTrattamento = Field(default=AreaTrattamento.RIABILITAZIONE)
    prezzo: float = Field(default=0.0)

    def __str__(self):
        return f"{self.nome} (€ {self.prezzo})"

# --- 5. PREVENTIVI (TESTATA) ---
class Preventivo(SQLModel, table=True):
    __tablename__ = "preventivi_testata_v5"
    id: Optional[int] = Field(default=None, primary_key=True)
    data: date = Field(default_factory=date.today)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_v5_stampa.id")
    paziente_rel: Optional[Paziente] = Relationship(back_populates="preventivi")

    oggetto: str = Field(default="Piano di Cura", description="Es: Ciclo spalla")
    totale: float = Field(default=0.0)
    note: Optional[str] = None

    # Righe
    righe: List["RigaPreventivo"] = Relationship(back_populates="preventivo")

    def __str__(self):
        return f"Prev. #{self.id} - {self.paziente_rel}"

# --- 6. PREVENTIVI (RIGHE - CARRELLO) ---
class RigaPreventivo(SQLModel, table=True):
    __tablename__ = "preventivi_righe_v5"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    preventivo_id: Optional[int] = Field(default=None, foreign_key="preventivi_testata_v5.id")
    preventivo: Optional[Preventivo] = Relationship(back_populates="righe")
    
    trattamento_id: Optional[int] = Field(default=None, foreign_key="listino_v5_stampa.id")
    trattamento: Optional[Trattamento] = Relationship()
    
    quantita: int = Field(default=1)
    sconto: float = Field(default=0.0)

# --- 7. SCADENZE (INTATTO) ---
class Scadenza(SQLModel, table=True):
    __tablename__ = "scadenze_v5"
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
