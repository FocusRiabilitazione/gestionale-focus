from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

# --- ENUMS ---
class AreaEnum(str, Enum):
    MANO = "Mano-Polso"
    COLONNA = "Colonna"
    ATM = "ATM"
    MUSCOLO = "Muscolo-Scheletrico"

class AreaPrestito(str, Enum):
    OGGETTI = "Oggetti"
    ELETTROMEDICALI = "Elettromedicali"

class AreaTrattamento(str, Enum):
    TERAPIA_MANUALE = "Terapia Manuale"
    STRUMENTALE = "Terapia Strumentale"
    PALESTRA = "Palestra/Riabilitazione"
    VISITA = "Visita Specialistica"

# --- PAZIENTI ---
class Paziente(SQLModel, table=True):
    __tablename__ = "pazienti_visite_v2"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cognome: str
    area: AreaEnum = Field(default=AreaEnum.MUSCOLO)
    note: Optional[str] = None
    disdetto: bool = False
    data_disdetta: Optional[date] = None
    visita_medica: bool = Field(default=False)
    data_visita: Optional[date] = None

    # Relazione inversa per vedere i preventivi del paziente
    preventivi: List["Preventivo"] = Relationship(back_populates="paziente_rel")

    def __str__(self):
        return f"{self.cognome} {self.nome}"

# --- LISTINO PREZZI (Trattamenti) ---
class Trattamento(SQLModel, table=True):
    __tablename__ = "listino_prezzi"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    area: AreaTrattamento = Field(default=AreaTrattamento.TERAPIA_MANUALE)
    prezzo_base: float = 0.0

    def __str__(self):
        return f"{self.nome} (€ {self.prezzo_base})"

# --- PREVENTIVI (TESTATA) ---
class Preventivo(SQLModel, table=True):
    __tablename__ = "preventivi_smart"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    data_creazione: date = Field(default_factory=date.today)
    
    # Collegamento al Paziente
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_visite_v2.id")
    paziente_rel: Optional[Paziente] = Relationship(back_populates="preventivi")

    descrizione_percorso: Optional[str] = Field(default=None, description="Es: Ciclo riabilitativo post-operatorio...")
    note_pagamento: Optional[str] = Field(default=None, description="Es: Acconto 50%, saldo a fine cura")
    
    totale_calcolato: float = Field(default=0.0)
    accettato: bool = False

    # Relazione con le righe (Inline)
    righe: List["RigaPreventivo"] = Relationship(back_populates="preventivo")

    def __str__(self):
        return f"Prev. #{self.id} - {self.data_creazione}"

# --- PREVENTIVI (RIGHE) ---
class RigaPreventivo(SQLModel, table=True):
    __tablename__ = "preventivi_righe"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    preventivo_id: Optional[int] = Field(default=None, foreign_key="preventivi_smart.id")
    preventivo: Optional[Preventivo] = Relationship(back_populates="righe")
    
    trattamento_id: Optional[int] = Field(default=None, foreign_key="listino_prezzi.id")
    trattamento: Optional[Trattamento] = Relationship()
    
    quantita: int = Field(default=1)
    sconto_unitario: float = Field(default=0.0)
    
    # Questo serve per fissare il prezzo al momento del preventivo (se il listino cambia)
    prezzo_applicato: float = 0.0 

# --- MAGAZZINO & PRESTITI (INVARIATI) ---
class Inventario(SQLModel, table=True):
    __tablename__ = "inventario_smart_v2"
    id: Optional[int] = Field(default=None, primary_key=True)
    materiale: str
    area_stanza: str 
    quantita: int = 0
    soglia_minima: int = 2
    obiettivo: int = 5

class Prestito(SQLModel, table=True):
    __tablename__ = "prestiti_smart_v1"
    id: Optional[int] = Field(default=None, primary_key=True)
    oggetto: str
    area: AreaPrestito = Field(default=AreaPrestito.OGGETTI)
    paziente_id: Optional[int] = Field(default=None, foreign_key="pazienti_visite_v2.id")
    paziente: Optional[Paziente] = Relationship()
    data_inizio: date = Field(default_factory=date.today)
    durata_giorni: int = Field(default=7)
    data_scadenza: Optional[date] = None 
    restituito: bool = False

class Scadenza(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descrizione: str
    importo: float
    data_scadenza: date
    pagato: bool = False
