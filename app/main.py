from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqladmin import Admin, ModelView, action, InlineModelAdmin
from sqlmodel import Session, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import (
    Paziente,
    Inventario,
    Prestito,
    Preventivo,
    Scadenza,
    Trattamento,
    RigaPreventivo
)

app = FastAPI(title="Gestionale Focus Rehab")

# =========================================================
# IMPORT MODELS
# =========================================================

class PazienteImport(BaseModel):
    nome: str
    cognome: str
    area: str

class InventarioImport(BaseModel):
    materiale: str
    area_stanza: str
    quantita: int = 0
    soglia_minima: int = 2
    obiettivo: int = 5

class PrestitoImport(BaseModel):
    oggetto: str
    area: str
    nome_paziente: str
    cognome_paziente: str
    durata_giorni: int = 7


# =========================================================
# STAMPA PREVENTIVO
# =========================================================

@app.get("/stampa_preventivo/{prev_id}", response_class=HTMLResponse)
def stampa_preventivo(prev_id: int):
    with Session(engine) as session:
        prev = session.get(Preventivo, prev_id)
        if not prev:
            return "Preventivo non trovato"

        righe_html = ""
        totale = 0

        for riga in prev.righe:
            if riga.trattamento:
                nome = riga.trattamento.nome
                prezzo = riga.trattamento.prezzo_base
            else:
                nome = "Servizio"
                prezzo = 0

            sub = (prezzo * riga.quantita) - riga.sconto
            totale += sub

            righe_html += f"""
            <tr>
                <td style='border-bottom:1px solid #ddd; padding:8px;'>{nome}</td>
                <td style='border-bottom:1px solid #ddd; padding:8px; text-align:center;'>{riga.quantita}</td>
                <td style='border-bottom:1px solid #ddd; padding:8px; text-align:right;'>€ {sub:.2f}</td>
            </tr>
            """

        html = f"""
        <html>
        <body style="font-family:Arial; padding:40px; max-width:800px; margin:auto;">
            <h1 style="text-align:center;">FOCUS REHAB</h1>
            <p><strong>Paziente:</strong> {prev.paziente_rel}</p>
            <p><strong>Data:</strong> {prev.data_creazione}</p>

            <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                <tr style="background:#eee;">
                    <th style="padding:10px; text-align:left;">Descrizione</th>
                    <th style="padding:10px;">Q.tà</th>
                    <th style="padding:10px; text-align:right;">Importo</th>
                </tr>
                {righe_html}
            </table>

            <h3 style="text-align:right; margin-top:30px;">
                TOTALE: € {totale:.2f}
            </h3>

            <div style="text-align:center; margin-top:40px;">
                <button onclick="window.print()">🖨️ STAMPA</button>
            </div>
        </body>
        </html>
        """

        return html


# =========================================================
# AZIONI MAGAZZINO
# =========================================================

@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)


@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0:
            item.quantita -= 1
            session.add(item)
            session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)


# =========================================================
# ADMIN
# =========================================================

class PazienteAdmin(ModelView, model=Paziente):
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area]
    column_searchable_list = [Paziente.cognome, Paziente.nome]


class InventarioAdmin(ModelView, model=Inventario):
    column_list = [
        Inventario.materiale,
        Inventario.area_stanza,
        Inventario.quantita,
        Inventario.soglia_minima,
        Inventario.obiettivo,
    ]


class PrestitoAdmin(ModelView, model=Prestito):
    column_list = [
        Prestito.area,
        Prestito.oggetto,
        Prestito.paziente,
        Prestito.data_scadenza,
    ]

    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni:
            model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)


# =========================================================
# LISTINO PREZZI
# =========================================================

class TrattamentoAdmin(ModelView, model=Trattamento):
    column_list = [Trattamento.nome, Trattamento.prezzo_base]


# =========================================================
# PREVENTIVI CON INLINE FUNZIONANTE
# =========================================================

class RigaPreventivoInline(InlineModelAdmin, model=RigaPreventivo):
    form_columns = [
        RigaPreventivo.trattamento,
        RigaPreventivo.quantita,
        RigaPreventivo.sconto,
    ]


class PreventivoAdmin(ModelView, model=Preventivo):
    inlines = [RigaPreventivoInline]

    column_list = [
        Preventivo.id,
        Preventivo.data_creazione,
        Preventivo.paziente_rel,
        Preventivo.totale_calcolato,
    ]

    form_columns = [
        Preventivo.paziente_rel,
        Preventivo.data_creazione,
        Preventivo.oggetto,
        Preventivo.note,
    ]

    async def after_model_change(self, data, model, is_created, request):
        tot = 0
        for riga in model.righe:
            if riga.trattamento:
                tot += (riga.trattamento.prezzo_base * riga.quantita) - riga.sconto
        model.totale_calcolato = tot


# =========================================================
# SCADENZE
# =========================================================

class ScadenzaAdmin(ModelView, model=Scadenza):
    column_list = [
        Scadenza.descrizione,
        Scadenza.data_scadenza,
        Scadenza.importo,
    ]


# =========================================================
# ATTIVAZIONE ADMIN
# =========================================================

admin = Admin(app, engine)

admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(TrattamentoAdmin)
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)


@app.on_event("startup")
def on_startup():
    init_db()
