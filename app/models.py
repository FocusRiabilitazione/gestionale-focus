from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from enum import Enum

# --- MENU A TENDINA PAZIENTI ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

# --- MENU A TENDINA MAGAZZINO ---
class AreaMagazzino(str, Enum):
    SEGRETERIA = "Segreteria"
    MANO = "Mano"
    STANZE = "Stanze"
    MEDICINALI = "Medicinali"
    PULIZIE = "Pulizie"

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    # Cambio versione per forzare l'aggiornamento
    __tablename__ = "pazienti_visite_v2" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    
    # Stati
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    
    # Nuovi campi
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    # Cambio versione per creare le colonne nuove
    __tablename__ = "inventario_smart_v2"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    
    # Menu a tendina magazzino
    area_stanza: AreaMagazzino = Field(default=AreaMagazzino.STANZE)
    
    # Campi numerici con valori di default per evitare errori
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- ALTRE TABELLE ---
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
