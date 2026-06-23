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
from .models import Ordine, ColoreDisponibile, ConfigSito, StatoOrdine, Tema, ElementoTema
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
        Ordine.tema_nome,
        Ordine.dimensione,
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

    def tema_cell(model, attribute):
        if model.tema_nome:
            return Markup(f'<span style="background:#ede9fe;color:#6d28d9;padding:2px 8px;border-radius:999px;font-size:.8em">{model.tema_emoji or ""} {model.tema_nome}</span>')
        return Markup('<span style="color:#9ca3af;font-size:.8em">–</span>')

    def pagato_icona(model, attribute):
        return Markup("✅" if model.pagamento_completato else "⏳")

    column_formatters = {
        Ordine.stato: stato_badge,
        Ordine.tema_nome: tema_cell,
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
        Ordine.tema_nome,
        Ordine.tema_emoji,
        Ordine.elementi_scelti,
        Ordine.prezzo_elementi,
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


class TemaAdmin(ModelView, model=Tema):
    name = "Tema"
    name_plural = "Temi"
    icon = "fa-solid fa-masks-theater"

    def tema_preview(model, attribute):
        return Markup(f'<span style="font-size:1.4em">{model.emoji}</span> <strong>{model.nome}</strong>')

    column_formatters = {Tema.nome: tema_preview}
    column_list = [Tema.nome, Tema.emoji, Tema.descrizione, Tema.disponibile, Tema.ordine_visualizzazione]
    form_columns = [Tema.nome, Tema.emoji, Tema.descrizione, Tema.disponibile, Tema.ordine_visualizzazione]


class ElementoTemaAdmin(ModelView, model=ElementoTema):
    name = "Decorazione"
    name_plural = "Decorazioni Tema"
    icon = "fa-solid fa-star"

    def elem_preview(model, attribute):
        return Markup(f'<span style="font-size:1.2em">{model.emoji}</span> {model.nome}')

    def prezzo_badge(model, attribute):
        return Markup(f'<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:999px;font-size:.85em">+€{model.prezzo_aggiuntivo:.0f}</span>')

    column_formatters = {ElementoTema.nome: elem_preview, ElementoTema.prezzo_aggiuntivo: prezzo_badge}
    column_list = [ElementoTema.tema, ElementoTema.nome, ElementoTema.emoji, ElementoTema.prezzo_aggiuntivo, ElementoTema.disponibile]
    form_columns = [ElementoTema.tema, ElementoTema.nome, ElementoTema.emoji, ElementoTema.descrizione, ElementoTema.prezzo_aggiuntivo, ElementoTema.disponibile]


class ConfigAdmin(ModelView, model=ConfigSito):
    name = "Impostazione"
    name_plural = "Impostazioni Sito"
    icon = "fa-solid fa-gear"
    column_list = [ConfigSito.chiave, ConfigSito.valore, ConfigSito.descrizione]
    form_columns = [ConfigSito.chiave, ConfigSito.valore, ConfigSito.descrizione]


admin = Admin(app, engine, title="🎀 Lettere Store – Admin")
admin.add_view(OrdineAdmin)
admin.add_view(ColoreAdmin)
admin.add_view(TemaAdmin)
admin.add_view(ElementoTemaAdmin)
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
            for i, (nome, hex_code) in enumerate([
                ("Bianco", "#FFFFFF"), ("Rosa", "#F9A8D4"), ("Lilla", "#C4B5FD"),
                ("Azzurro", "#93C5FD"), ("Menta", "#6EE7B7"), ("Giallo", "#FDE68A"),
                ("Oro", "#D4AF37"), ("Argento", "#C0C0C0"),
            ], start=1):
                session.add(ColoreDisponibile(nome=nome, hex_code=hex_code, ordine_visualizzazione=i))

        # Temi di default
        if not session.exec(select(Tema)).first():
            temi_default = [
                ("Safari", "🦁", "Animali della savana", 1, [
                    ("Leone", "🦁", 5.0), ("Elefante", "🐘", 5.0),
                    ("Giraffa", "🦒", 5.0), ("Zebra", "🦓", 5.0),
                ]),
                ("Principessa", "👸", "Fate, castelli e unicorni", 2, [
                    ("Corona", "👑", 5.0), ("Castello", "🏰", 5.0),
                    ("Unicorno", "🦄", 5.0), ("Fata", "🧚", 5.0),
                ]),
                ("Spazio", "🚀", "Pianeti, stelle e razzi", 3, [
                    ("Razzo", "🚀", 5.0), ("Luna", "🌙", 5.0),
                    ("Stella", "⭐", 5.0), ("Pianeta", "🪐", 5.0),
                ]),
                ("Mare", "🌊", "Pesci, conchiglie e delfini", 4, [
                    ("Delfino", "🐬", 5.0), ("Conchiglia", "🐚", 5.0),
                    ("Pesce", "🐠", 5.0), ("Polpo", "🐙", 5.0),
                ]),
                ("Dinosauri", "🦕", "Triceratopo, T-Rex e amici", 5, [
                    ("T-Rex", "🦖", 5.0), ("Diplodoco", "🦕", 5.0),
                    ("Pterodattilo", "🦅", 5.0),
                ]),
                ("Fiori", "🌸", "Rose, margherite e farfalle", 6, [
                    ("Rosa", "🌹", 5.0), ("Margherita", "🌼", 5.0),
                    ("Farfalla", "🦋", 5.0), ("Coccinella", "🐞", 5.0),
                ]),
            ]
            for nome, emoji, desc, ordine, elementi in temi_default:
                tema = Tema(nome=nome, emoji=emoji, descrizione=desc, ordine_visualizzazione=ordine)
                session.add(tema)
                session.flush()
                for e_nome, e_emoji, e_prezzo in elementi:
                    session.add(ElementoTema(tema_id=tema.id, nome=e_nome, emoji=e_emoji, prezzo_aggiuntivo=e_prezzo))

        # Config di default
        for chiave, valore, desc in [
            ("nome_negozio", "Piccolettere", "Nome visualizzato nel sito"),
            ("telefono", "+39 000 000 0000", "Numero WhatsApp/telefono"),
            ("email_contatto", "info@letteredelcuore.it", "Email pubblica"),
            ("instagram", "", "URL profilo Instagram"),
            ("tempi_consegna", "7-10 giorni lavorativi", "Tempi di consegna indicativi"),
            ("spese_spedizione", "5.90", "Spese di spedizione in euro (0 = gratuita)"),
        ]:
            if not session.exec(select(ConfigSito).where(ConfigSito.chiave == chiave)).first():
                session.add(ConfigSito(chiave=chiave, valore=valore, descrizione=desc))

        session.commit()
