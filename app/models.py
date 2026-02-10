from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from enum import Enum  # <--- Importiamo Enum per fare il menu nativo

# 1. DEFINIAMO LE SCELTE QUI (Non nel main)
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    # Usiamo un nome nuovo per garantire che il DB crei il tipo Enum corretto
    __tablename__ = "pazienti_auto" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    
    # 2. COLLEGHIAMO IL MENU
    # Dicendo che 'area' è di tipo 'AreaEnum', il menu appare da solo!
    area: AreaEnum 
    
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    visita_esterna: bool = False
    data_visita: Optional[date] = None

# --- ALTRE TABELLE (Uguali a prima) ---
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
