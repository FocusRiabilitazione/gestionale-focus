from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

# --- MENU A TENDINA PAZIENTI ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

# --- NUOVO MENU A TENDINA PRESTITI ---
class AreaPrestito(str, Enum):
    OGGETTI = "Oggetti"
    ELETTROMEDICALI = "Elettromedicali"

# --- ANAGRAFICA PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_visite_v2" # Manteniamo la tabella pazienti esistente
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None

    # Serve per far vedere il nome nel menu a tendina dei prestiti
    def __str__(self):
        return f"{self.cognome} {self.nome}"

# --- MAGAZZINO ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_smart_v2"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = Field(default=0)
    soglia_minima: int = Field(default=2)
    obiettivo: int = Field(default=5)

# --- PRESTITI (NUOVO E POTENTE) ---
class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_smart_v1"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 1. Cosa prestiamo?
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    
    # 2. A chi? (Collegamento intelligente al Paziente)
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_visite_v2.id")
    paziente: Optional[Paziente] = Relationship()

    # 3. Tempo
    data_inizio: date = Field(default_factory=date.today) # Parte da oggi in automatico
    durata_giorni: int = Field(default=7) # Default 1 settimana
    data_scadenza: Optional[date] = None # Calcolata dal sistema
    
    # 4. Stato
    restituito: bool = False

# --- ALTRE TABELLE ---
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
