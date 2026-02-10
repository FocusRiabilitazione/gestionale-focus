from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_v7" # Nuova tabella, zero errori
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: str 
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
# --- ALTRE TABELLE ---
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    quantita: int = 0
    area_stanza: str 

class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente_nome: str 
    oggetto: str
    data_scadenza: date
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
