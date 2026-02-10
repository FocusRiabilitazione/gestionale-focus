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

# --- PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_v3_fix"  # <--- NUOVO NOME PER FORZARE IL RESET
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None

    def __str__(self):
        return f"{self.cognome} {self.nome}"

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_v3_fix" # <--- NUOVO NOME PER FORZARE IL RESET
    
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- PRESTITI ---
class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_v3_fix" # <--- NUOVO NOME PER FORZARE IL RESET
    
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_v3_fix.id")
    paziente: Optional[Paziente] = Relationship()

    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

# --- ALTRE TABELLE ---
class Preventivo(SQLModel, table=True):
    __tablename__ = "preventivi_v3_fix"
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    totale: float
    data_creazione: date = Field(default_factory=date.today)

class Scadenza(SQLModel, table=True):
    __tablename__ = "scadenze_v3_fix"
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
