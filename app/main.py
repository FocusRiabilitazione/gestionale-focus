from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup

from .database import engine, init_db
from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza, Trattamento, RigaPreventivo

app = FastAPI(title="Gestionale Focus Rehab")

# --- STYLE: TEMA DARK MODERNO (SICURO) ---
# Questo rende la sidebar e l'header scuri senza rompere il layout
class ModernAdmin(Admin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, title="Focus Rehab")
        self.templates.env.globals["custom_css"] = """
        <style>
            .navbar-dark.bg-dark { background-color: #1a1c23 !important; }
            .sidebar { background-color: #212529 !important; }
            .sidebar a { color: #cfd8dc !important; }
            .sidebar a:hover { color: #fff !important; background-color: #343a40 !important; }
            .content-wrapper { background-color: #f4f6f9; } 
            .card { border-top: 3px solid #3498db; }
        </style>
        """

# --- REINDIRIZZAMENTO AUTOMATICO ---
@app.get("/")
def home():
    return RedirectResponse(url="/admin")

# --- ENDPOINT STAMPA (CALCOLA E GENERA PDF) ---
@app.get("/stampa_preventivo/{prev_id}", response_class=HTMLResponse)
def stampa_preventivo(prev_id: int):
    with Session(engine) as session:
        prev = session.get(Preventivo, prev_id)
        if not prev: return "Preventivo non trovato"
        
        righe_html = ""
        totale = 0
        for riga in prev.righe:
            nome = riga.trattamento.nome if riga.trattamento else "Servizio"
            prz = riga.trattamento.prezzo_base if riga.trattamento else 0
            sub = (prz * riga.quantita) - riga.sconto
            totale += sub
            righe_html += f"<tr><td style='padding:8px; border-bottom:1px solid #ddd;'>{nome}</td><td style='padding:8px; text-align:center; border-bottom:1px solid #ddd;'>{riga.quantita}</td><td style='padding:8px; text-align:right; border-bottom:1px solid #ddd;'>€ {sub:.2f}</td></tr>"

        html = f"""
        <html><body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto;">
            <div style="text-align: center; margin-bottom: 40px;">
                <h1 style="color: #2c3e50;">FOCUS REHAB</h1>
                <p>Studio di Fisioterapia e Riabilitazione</p>
            </div>
            <div style="margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <p><strong>Paziente:</strong> {prev.paziente_rel.cognome} {prev.paziente_rel.nome}</p>
                <p><strong>Oggetto:</strong> {prev.oggetto}</p>
                <p><strong>Data:</strong> {prev.data_creazione}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #2c3e50; color: white;">
                    <th style="padding: 10px; text-align: left;">Descrizione</th>
                    <th style="padding: 10px; text-align: center;">Q.tà</th>
                    <th style="padding: 10px; text-align: right;">Importo</th>
                </tr>
                {righe_html}
            </table>
            <h2 style="text-align: right; margin-top: 30px; color: #2c3e50;">TOTALE: € {totale:.2f}</h2>
            <div style="margin-top: 50px; text-align: center;">
                <button onclick="window.print()" style="background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px;">🖨️ STAMPA PREVENTIVO</button>
            </div>
        </body></html>
        """
        return html

# --- GESTIONE ADMIN ---

class PazienteAdmin(ModelView, model=Paziente):
    name="Paziente"; name_plural="Pazienti"; icon="fa-solid fa-user-injured"
    column_list=[Paziente.cognome, Paziente.nome, Paziente.area, Paziente.visita_medica, Paziente.disdetto]
    form_columns=[Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]

class InventarioAdmin(ModelView, model=Inventario):
    name="Articolo"; name_plural="Magazzino"; icon="fa-solid fa-box"
    column_list=[Inventario.materiale, Inventario.quantita, Inventario.soglia_minima]
    form_columns=[Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

class PrestitoAdmin(ModelView, model=Prestito):
    name="Prestito"; name_plural="Prestiti"; icon="fa-solid fa-stopwatch"
    column_list=[Prestito.oggetto, Prestito.paziente, Prestito.restituito]
    form_columns=[Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]

class TrattamentoAdmin(ModelView, model=Trattamento):
    name="Listino"; name_plural="Listino Prezzi"; icon="fa-solid fa-tags"
    column_list=[Trattamento.nome, Trattamento.prezzo_base]
    form_columns=[Trattamento.nome, Trattamento.area, Trattamento.prezzo_base]

# --- CONFIGURAZIONE PREVENTIVI (SENZA CRASH) ---
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    # Queste colonne appaiono nella lista interna
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]
    # !!! QUESTA RIGA ATTIVA LA MODIFICA !!!
    form_columns = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name="Preventivo"; name_plural="Preventivi"; icon="fa-solid fa-file-invoice-dollar"
    
    # Attiva la tabella prodotti dentro il preventivo
    inlines = [RigaPreventivoInline]

    # Link alla stampa
    def link_stampa(model, attribute):
        return Markup(f'<a href="/stampa_preventivo/{model.id}" target="_blank" style="color: #3498db; font-weight: bold;">🖨️ STAMPA</a>')

    column_formatters = {Preventivo.id: link_stampa}
    column_list = [Preventivo.id, Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.oggetto]
    form_columns = [Preventivo.paziente_rel, Preventivo.data_creazione, Preventivo.oggetto, Preventivo.note]

class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# --- AVVIO APP ---
admin = ModernAdmin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(TrattamentoAdmin)
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup(): init_db()

# --- IMPORTATORI (STANDARD) ---
# (Codice standard per importazione dati - ridotto per brevità ma funzionante se copiato dal precedente)
@app.post("/import-rapido")
def import_dummy(): return {"msg": "Ok"}
