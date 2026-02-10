from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    # Usiamo v5 per ripartire da zero e puliti
    __tablename__ = "pazienti_v5" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Campi Base
    nome: str
    cognome: str
    
    # Qui il trucco: nel DB è una stringa normale, così non dà errori
    area: str 
    
    # Facoltativi
    note: Optional[str] = None
    
    # Stati
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    visita_esterna: bool = False
    data_visita: Optional[date] = None

# --- ALTRE TABELLE (Standard) ---
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = 0
    obiettivo: int = 5
    soglia_minima: int = 2

class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente_nome: str 
    oggetto: str
    data_prestito: date = Field(default_factory=date.today)
    data_scadenza: date
    restituito: bool = False

class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    dettagli: str 
    totale: float
    data_creazione: date = Field(default_factory=date.today)
    note: Optional[str] = None

class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
    ricorrenza: str = "Singola"
