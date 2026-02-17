from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

# --- ENUMS ---
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

# --- PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_table_v9"
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

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_table_v9"
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- PRESTITI ---
class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_table_v9"
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_table_v9.id")
    paziente: Optional[Paziente] = Relationship()
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

# --- LISTINO PREZZI ---
class Trattamento(SQLModel, table=True):
    __tablename__ = "listino_prezzi_v9" 
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    prezzo_base: float = Field(default=0.0)

    def __str__(self):
        return f"{self.nome} (€ {self.prezzo_base})"

# --- PREVENTIVI (TESTATA) ---
class Preventivo(SQLModel, table=True):
    __tablename__ = "preventivi_testata_v9"
    id: Optional[int] = Field(default=None, primary_key=True)
    data_creazione: date = Field(default_factory=date.today)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_table_v9.id")
    paziente_rel: Optional[Paziente] = Relationship(back_populates="preventivi")

    oggetto: str = Field(default="Piano di cura", description="Es: Ciclo riabilitativo")
    note: Optional[str] = None

    # Relazione con le righe
    righe: List["RigaPreventivo"] = Relationship(back_populates="preventivo")

    def __str__(self):
        return f"Prev. #{self.id} - {self.data_creazione}"

# --- PREVENTIVI (RIGHE) ---
class RigaPreventivo(SQLModel, table=True):
    __tablename__ = "preventivi_righe_v9"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    preventivo_id: Optional[int] = Field(default=None, foreign_key="preventivi_testata_v9.id")
    preventivo: Optional[Preventivo] = Relationship(back_populates="righe")
    
    trattamento_id: Optional[int] = Field(default=None, foreign_key="listino_prezzi_v9.id")
    trattamento: Optional[Trattamento] = Relationship()
    
    quantita: int = Field(default=1)
    sconto: float = Field(default=0.0)

# --- SCADENZARIO ---
class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
