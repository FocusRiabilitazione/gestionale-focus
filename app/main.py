from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqladmin import Admin, ModelView, action
from sqlmodel import SQLModel, Session, select
from datetime import date, timedelta
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from typing import List
from markupsafe import Markup
from sqlalchemy import create_engine

# --- DATABASE SETUP (Nuovo nome = Database Pulito) ---
sqlite_file_name = "database_v5_stampa.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

from .models import Paziente, Inventario, Prestito, Preventivo, Scadenza, Trattamento, RigaPreventivo

app = FastAPI(title="Gestionale Focus Rehab")

# ==========================================
# 1. FUNZIONE SPECIALE: GENERATORE DI STAMPA
# ==========================================
@app.get("/stampa/{prev_id}", response_class=HTMLResponse)
def stampa_preventivo(prev_id: int):
    """
    Questa funzione crea una pagina web pulita, perfetta per essere stampata su A4.
    """
    with Session(engine) as session:
        prev = session.get(Preventivo, prev_id)
        if not prev:
            return "Preventivo non trovato"
        
        # Calcolo righe al volo per la visualizzazione
        righe_html = ""
        totale_calcolato = 0
        for riga in prev.righe:
            nome_tratt = riga.trattamento.nome if riga.trattamento else "Servizio rimosso"
            prezzo_unit = riga.trattamento.prezzo if riga.trattamento else 0
            subtotale = (prezzo_unit * riga.quantita) - riga.sconto
            totale_calcolato += subtotale
            
            righe_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px;">{nome_tratt}</td>
                <td style="padding: 8px; text-align: center;">{riga.quantita}</td>
                <td style="padding: 8px; text-align: right;">€ {prezzo_unit:.2f}</td>
                <td style="padding: 8px; text-align: right;">€ {riga.sconto:.2f}</td>
                <td style="padding: 8px; text-align: right;"><b>€ {subtotale:.2f}</b></td>
            </tr>
            """

        # HTML DEL FOGLIO A4
        html_content = f"""
        <html>
        <head>
            <title>Stampa Preventivo #{prev.id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px; color: #333; }}
                .header {{ text-align: center; margin-bottom: 40px; border-bottom: 2px solid #0056b3; padding-bottom: 20px; }}
                .info {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th {{ background: #f0f0f0; text-align: left; padding: 10px; border-bottom: 2px solid #ccc; }}
                .totale {{ text-align: right; font-size: 1.5em; margin-top: 20px; color: #0056b3; }}
                .footer {{ margin-top: 50px; font-size: 0.8em; text-align: center; color: #777; }}
                @media print {{ .no-print {{ display: none; }} }}
            </style>
        </head>
        <body>
            <button class="no-print" onclick="window.print()" style="padding: 10px 20px; background: #0056b3; color: white; border: none; cursor: pointer; font-size: 16px;">🖨️ STAMPA ORA</button>
            <br><br>
            
            <div class="header">
                <h1>FOCUS REHAB</h1>
                <p>Studio di Fisioterapia e Riabilitazione</p>
            </div>

            <div class="info">
                <div>
                    <strong>Spett.le Paziente:</strong><br>
                    {prev.paziente_rel.cognome} {prev.paziente_rel.nome}<br>
                </div>
                <div style="text-align: right;">
                    <strong>Preventivo N. {prev.id}</strong><br>
                    Data: {prev.data}<br>
                    Oggetto: {prev.oggetto}
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Descrizione</th>
                        <th style="text-align: center;">Q.tà</th>
                        <th style="text-align: right;">Prezzo</th>
                        <th style="text-align: right;">Sconto</th>
                        <th style="text-align: right;">Totale</th>
                    </tr>
                </thead>
                <tbody>
                    {righe_html}
                </tbody>
            </table>

            <div class="totale">
                <strong>TOTALE PREVENTIVATO: € {totale_calcolato:.2f}</strong>
            </div>
            
            <div class="footer">
                <p>{prev.note if prev.note else ""}</p>
                <p>Grazie per la fiducia. Focus Rehab.</p>
            </div>
        </body>
        </html>
        """
        return html_content

# ==========================================
# 2. CONFIGURAZIONE INTERFACCIA (Admin)
# ==========================================

# Formattatore per il Link di Stampa
def link_stampa(model, attribute):
    return Markup(f'<a href="/stampa/{model.id}" target="_blank" style="text-decoration:none; font-size:1.2em;">🖨️</a>')

# Formattatore per i Bottoni Magazzino
def formatta_bottoni(model, attribute):
    q = model.quantita if model.quantita is not None else 0
    s = model.soglia_minima if model.soglia_minima is not None else 0
    o = model.obiettivo if model.obiettivo is not None else 0
    if q <= s: stato = f"🔴 {q}"
    elif q >= o: stato = f"🌟 {q}"
    else: stato = f"✅ {q}"
    style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; background:#f9f9f9;"
    return Markup(f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a> <b>{stato}</b> <a href="/magazzino/piu/{model.id}" style="{style}">➕</a>')

# Viste
class PazienteAdmin(ModelView, model=Paziente):
    name="Paziente"; name_plural="Pazienti"; icon="fa-solid fa-user-injured"
    column_list=[Paziente.cognome, Paziente.nome, Paziente.area, Paziente.disdetto]
    form_columns=[Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]

class InventarioAdmin(ModelView, model=Inventario):
    name="Articolo"; name_plural="Magazzino"; icon="fa-solid fa-box"
    column_formatters={Inventario.quantita: formatta_bottoni}
    column_list=[Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima]
    form_columns=[Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

class PrestitoAdmin(ModelView, model=Prestito):
    name="Prestito"; name_plural="Prestiti"; icon="fa-solid fa-stopwatch"
    def list_query(self, request): return select(Prestito).where(Prestito.restituito == False)
    column_list=[Prestito.oggetto, Prestito.paziente, Prestito.data_scadenza]
    form_columns=[Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]

class TrattamentoAdmin(ModelView, model=Trattamento):
    name="Servizio/Listino"; name_plural="Listino Prezzi"; icon="fa-solid fa-tags"
    column_list=[Trattamento.area, Trattamento.nome, Trattamento.prezzo]
    form_columns=[Trattamento.nome, Trattamento.area, Trattamento.prezzo]

class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name="Preventivo"; name_plural="Preventivi (Stampa)"; icon="fa-solid fa-file-invoice"
    # Qui appare l'icona stampante nella lista
    column_formatters = {Preventivo.id: link_stampa} 
    column_list=[Preventivo.id, Preventivo.data, Preventivo.paziente_rel, Preventivo.totale]
    # Qui inserisci le righe dentro il preventivo
    inlines = [RigaPreventivoInline]
    form_columns=[Preventivo.paziente_rel, Preventivo.data, Preventivo.oggetto, Preventivo.note]

    # Calcolo totale automatico quando salvi
    async def after_model_change(self, data, model, is_created, request):
        with Session(engine) as session:
            stmt = select(Preventivo).where(Preventivo.id == model.id)
            prev = session.exec(stmt).first()
            if prev and prev.righe:
                tot = 0
                for riga in prev.righe:
                    if riga.trattamento:
                        tot += (riga.trattamento.prezzo * riga.quantita) - riga.sconto
                prev.totale = tot
                session.add(prev); session.commit()

class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# --- APP START ---
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

# --- ENDPOINT RAPIDI ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item: item.quantita += 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0: item.quantita -= 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

# Importatori (Semplificati per brevità, ma presenti)
class PazienteImport(BaseModel):
    nome: str; cognome: str; area: str
@app.post("/import-rapido")
def import_pazienti(l: List[PazienteImport]):
    with Session(engine) as s:
        for p in l: s.add(Paziente(nome=p.nome, cognome=p.cognome, area=p.area))
        s.commit()
    return {"msg": "Ok"}

@app.get("/")
def home(): return {"msg": "Focus Rehab - Sistema Pronto per la Stampa"}
