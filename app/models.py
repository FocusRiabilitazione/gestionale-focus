from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Campi Obbligatori
    nome: str
    cognome: str
    area: str  # Menu a tendina
    
    # Campi Facoltativi (Note è l'unico rimasto)
    note: Optional[str] = None
    
    # Stati (Gestiti dai pulsanti)
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    visita_esterna: bool = False
    data_visita: Optional[date] = None

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = 0
    obiettivo: int = 5
    soglia_minima: int = 2

# --- PRESTITI ---
class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente_nome: str 
    oggetto: str
    data_prestito: date = Field(default_factory=date.today)
    data_scadenza: date
    restituito: bool = False

# --- PREVENTIVI ---
class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    dettagli: str 
    totale: float
    data_creazione: date = Field(default_factory=date.today)
    note: Optional[str] = None

# --- SCADENZE ---
class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
    ricorrenza: str = "Singola"
