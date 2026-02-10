from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from enum import Enum # <--- Importiamo questo per il menu a tendina nativo

# --- DEFINIZIONE MENU A TENDINA ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    # Usiamo v4 per essere sicuri che crei la tabella nuova compatibile col menu
    __tablename__ = "pazienti_v4" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Campi Obbligatori
    nome: str
    cognome: str
    
    # QUI LA MAGIA: Usando AreaEnum, il sistema crea da solo il menu a tendina!
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    
    # Campi Facoltativi
    note: Optional[str] = None
    
    # Stati
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    visita_esterna: bool = False
    data_visita: Optional[date] = None

# --- ALTRE TABELLE (Rimangono uguali) ---
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
