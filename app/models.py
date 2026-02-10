from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from enum import Enum

# --- DEFINIZIONE MENU A TENDINA ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    # Cambio nome per forzare l'aggiunta delle nuove colonne
    __tablename__ = "pazienti_visite_v1" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    
    # Menu a tendina nativo
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    
    note: Optional[str] = None
    
    # DISDETTE
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    # NUOVI CAMPI: VISITE MEDICHE (Manuale)
    visita_medica: bool = Field(default=False, description="Deve fare una visita?")
    data_visita: Optional[date] = None

# --- ALTRE TABELLE (INVARIATE) ---
class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    quantita: int = 0
    area_stanza: str 
    obiettivo: int = 5
    soglia_minima: int = 2

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
