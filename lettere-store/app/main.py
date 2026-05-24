import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqladmin import Admin, ModelView
from sqlmodel import Session, select
from markupsafe import Markup
from datetime import datetime

from .database import engine, init_db
from .models import Ordine, ColoreDisponibile, ConfigSito, StatoOrdine
from .routes.shop import router as shop_router
from .routes.checkout import router as checkout_router

app = FastAPI(title="Lettere Personalizzate")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(shop_router)
app.include_router(checkout_router)

# ─── ADMIN ────────────────────────────────────────────────────────────────────

class OrdineAdmin(ModelView, model=Ordine):
    name = "Ordine"
    name_plural = "Ordini"
    icon = "fa-solid fa-bag-shopping"
    column_list = [
        Ordine.codice_ordine,
        Ordine.data_ordine,
        Ordine.nome,
        Ordine.cognome,
        Ordine.lettera_iniziale,
        Ordine.nome_personalizzato,
        Ordine.dimensione,
        Ordine.tipo_evento,
        Ordine.totale,
        Ordine.stato,
        Ordine.pagamento_completato,
    ]
    column_searchable_list = [Ordine.cognome, Ordine.nome, Ordine.codice_ordine, Ordine.email]
    column_sortable_list = [Ordine.data_ordine, Ordine.totale, Ordine.stato]
    column_default_sort = [(Ordine.data_ordine, True)]

    def stato_badge(model, attribute):
        colori = {
            "In attesa di pagamento": "background:#fbbf24;color:#000",
            "Pagato": "background:#34d399;color:#000",
            "In lavorazione": "background:#60a5fa;color:#000",
            "Spedito": "background:#a78bfa;color:#000",
            "Consegnato": "background:#6ee7b7;color:#000",
            "Annullato": "background:#f87171;color:#fff",
        }
        style = colori.get(model.stato, "background:#e5e7eb;color:#000")
        return Markup(f'<span style="padding:3px 10px;border-radius:999px;font-size:0.8em;{style}">{model.stato}</span>')

    def pagato_icona(model, attribute):
        return Markup("✅" if model.pagamento_completato else "⏳")

    column_formatters = {
        Ordine.stato: stato_badge,
        Ordine.pagamento_completato: pagato_icona,
    }
    form_columns = [
        Ordine.stato,
        Ordine.note_cliente,
        Ordine.nome,
        Ordine.cognome,
        Ordine.email,
        Ordine.telefono,
        Ordine.lettera_iniziale,
        Ordine.nome_personalizzato,
        Ordine.colore_nome,
        Ordine.dimensione,
        Ordine.tipo_evento,
        Ordine.indirizzo,
        Ordine.citta,
        Ordine.cap,
        Ordine.provincia,
        Ordine.totale,
        Ordine.pagamento_completato,
        Ordine.metodo_pagamento,
        Ordine.pagamento_id,
    ]


class ColoreAdmin(ModelView, model=ColoreDisponibile):
    name = "Colore"
    name_plural = "Colori Disponibili"
    icon = "fa-solid fa-palette"

    def anteprima_colore(model, attribute):
        return Markup(
            f'<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:{model.hex_code};border:1px solid #ccc;vertical-align:middle;margin-right:6px;"></span>{model.nome}'
        )

    column_formatters = {ColoreDisponibile.nome: anteprima_colore}
    column_list = [ColoreDisponibile.nome, ColoreDisponibile.hex_code, ColoreDisponibile.disponibile, ColoreDisponibile.ordine_visualizzazione]
    form_columns = [ColoreDisponibile.nome, ColoreDisponibile.hex_code, ColoreDisponibile.disponibile, ColoreDisponibile.ordine_visualizzazione]


class ConfigAdmin(ModelView, model=ConfigSito):
    name = "Impostazione"
    name_plural = "Impostazioni Sito"
    icon = "fa-solid fa-gear"
    column_list = [ConfigSito.chiave, ConfigSito.valore, ConfigSito.descrizione]
    form_columns = [ConfigSito.chiave, ConfigSito.valore, ConfigSito.descrizione]


admin = Admin(app, engine, title="🎀 Lettere Store – Admin")
admin.add_view(OrdineAdmin)
admin.add_view(ColoreAdmin)
admin.add_view(ConfigAdmin)


# ─── STARTUP ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()
    _seed_dati_iniziali()


def _seed_dati_iniziali():
    with Session(engine) as session:
        # Colori di default
        if not session.exec(select(ColoreDisponibile)).first():
            colori = [
                ColoreDisponibile(nome="Bianco", hex_code="#FFFFFF", ordine_visualizzazione=1),
                ColoreDisponibile(nome="Rosa", hex_code="#F9A8D4", ordine_visualizzazione=2),
                ColoreDisponibile(nome="Lilla", hex_code="#C4B5FD", ordine_visualizzazione=3),
                ColoreDisponibile(nome="Azzurro", hex_code="#93C5FD", ordine_visualizzazione=4),
                ColoreDisponibile(nome="Menta", hex_code="#6EE7B7", ordine_visualizzazione=5),
                ColoreDisponibile(nome="Giallo", hex_code="#FDE68A", ordine_visualizzazione=6),
                ColoreDisponibile(nome="Oro", hex_code="#D4AF37", ordine_visualizzazione=7),
                ColoreDisponibile(nome="Argento", hex_code="#C0C0C0", ordine_visualizzazione=8),
            ]
            for c in colori:
                session.add(c)

        # Config di default
        config_default = [
            ("nome_negozio", "Lettere del Cuore", "Nome visualizzato nel sito"),
            ("telefono", "+39 000 000 0000", "Numero WhatsApp/telefono"),
            ("email_contatto", "info@letteredelcuore.it", "Email pubblica"),
            ("instagram", "", "URL profilo Instagram"),
            ("tempi_consegna", "7-10 giorni lavorativi", "Tempi di consegna indicativi"),
            ("spese_spedizione", "5.90", "Spese di spedizione in euro (0 = gratuita)"),
        ]
        for chiave, valore, desc in config_default:
            existing = session.exec(select(ConfigSito).where(ConfigSito.chiave == chiave)).first()
            if not existing:
                session.add(ConfigSito(chiave=chiave, valore=valore, descrizione=desc))

        session.commit()
