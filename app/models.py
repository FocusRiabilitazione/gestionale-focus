from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Dati Base
    nome: str
    cognome: str
    codice_fiscale: Optional[str] = None  # Utile per fatture
    
    # Contatti
    telefono: Optional[str] = None
    email: Optional[str] = None
    
    # Gestione Clinica
    area: str = "Altro" # Es: "Mano", "Colonna", "ATM"
    
    # Stati (Flag)
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    visita_esterna: bool = False
    data_visita: Optional[date] = None
    
    note: Optional[str] = None

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str # Es: "Segreteria", "Mano", "Stanza 1"
    quantita: int = 0
    obiettivo: int = 5
    soglia_minima: int = 2

# --- PRESTITI ---
class Prestito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente_nome: str # Salviamo nome e cognome per semplicità
    oggetto: str
    data_prestito: date = Field(default_factory=date.today)
    data_scadenza: date
    restituito: bool = False

# --- PREVENTIVI ---
class Preventivo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paziente: str
    dettagli: str # Es: "Tecar x5, Laser x3"
    totale: float
    data_creazione: date = Field(default_factory=date.today)
    note: Optional[str] = None

# --- SCADENZE PAGAMENTI ---
class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
    ricorrenza: str = "Singola"

