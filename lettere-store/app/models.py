from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
import uuid


class TipoEvento(str, Enum):
    BATTESIMO = "Battesimo"
    COMPLEANNO = "Compleanno"
    NASCITA = "Nascita"
    COMUNIONE = "Prima Comunione"
    ALTRO = "Altro"


class StatoOrdine(str, Enum):
    IN_ATTESA_PAGAMENTO = "In attesa di pagamento"
    PAGATO = "Pagato"
    IN_LAVORAZIONE = "In lavorazione"
    SPEDITO = "Spedito"
    CONSEGNATO = "Consegnato"
    ANNULLATO = "Annullato"


class MetodoPagamento(str, Enum):
    STRIPE = "Carta di credito"
    PAYPAL = "PayPal"


class Dimensione(str, Enum):
    PICCOLA = "Piccola (15cm)"
    MEDIA = "Media (20cm)"
    GRANDE = "Grande (30cm)"


class ColoreDisponibile(SQLModel, table=True):
    __tablename__ = "colori_lettere"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    hex_code: str = Field(default="#FFFFFF")
    disponibile: bool = Field(default=True)
    ordine_visualizzazione: int = Field(default=0)

    def __str__(self):
        return self.nome


class ConfigSito(SQLModel, table=True):
    __tablename__ = "config_sito_lettere"
    id: Optional[int] = Field(default=None, primary_key=True)
    chiave: str = Field(unique=True)
    valore: str
    descrizione: Optional[str] = None


class Ordine(SQLModel, table=True):
    __tablename__ = "ordini_lettere"
    id: Optional[int] = Field(default=None, primary_key=True)
    codice_ordine: str = Field(default_factory=lambda: f"LTR-{uuid.uuid4().hex[:8].upper()}")

    # Dati cliente
    nome: str
    cognome: str
    email: str
    telefono: Optional[str] = None

    # Personalizzazione prodotto
    lettera_iniziale: str = Field(max_length=1)
    nome_personalizzato: str
    colore_nome: Optional[str] = None
    colore_hex: Optional[str] = None
    dimensione: Dimensione = Field(default=Dimensione.MEDIA)
    tipo_evento: TipoEvento = Field(default=TipoEvento.BATTESIMO)
    note_cliente: Optional[str] = None

    # Spedizione
    indirizzo: str
    citta: str
    cap: str
    provincia: str

    # Ordine
    prezzo_unitario: float = Field(default=0.0)
    totale: float = Field(default=0.0)
    stato: StatoOrdine = Field(default=StatoOrdine.IN_ATTESA_PAGAMENTO)
    metodo_pagamento: Optional[MetodoPagamento] = None
    pagamento_id: Optional[str] = None
    pagamento_completato: bool = Field(default=False)

    data_ordine: datetime = Field(default_factory=datetime.utcnow)
    data_aggiornamento: Optional[datetime] = None

    def __str__(self):
        return f"Ordine {self.codice_ordine} - {self.nome} {self.cognome}"
