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

# --- NUOVO MENU A TENDINA MAGAZZINO ---
class AreaMagazzino(str, Enum):
    SEGRETERIA = "Segreteria"
    MANO = "Mano"
    STANZE = "Stanze"
    MEDICINALI = "Medicinali"
    PULIZIE = "Pulizie"

# --- ANAGRAFICA PAZIENTI (Invariata) ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_visite_v1" 
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None

# --- MAGAZZINO (AGGIORNATO) ---
class Inventario(SQLModel, table=True):
    # Cambio nome per creare la tabella nuova pulita
    __tablename__ = "inventario_smart_v1"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    materiale: str
    
    # Menu a tendina collegato alla lista sopra
    area_stanza: AreaMagazzino = Field(default=AreaMagazzino.STANZE)
    
    quantita: int = Field(default=0, description="Quanti ne abbiamo ora")
    soglia_minima: int = Field(default=2, description="Quando scatta l'allarme")
    obiettivo: int = Field(default=5, description="Quanti dovremmo averne")

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
