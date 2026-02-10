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

# --- STRUTTURE IMPORTAZIONE ---
class PazienteImport(BaseModel):
    nome: str; cognome: str; area: str
class InventarioImport(BaseModel):
    materiale: str; area_stanza: str; quantita: int=0; soglia_minima: int=2; obiettivo: int=5
class PrestitoImport(BaseModel):
    oggetto: str; area: str; nome_paziente: str; cognome_paziente: str; durata_giorni: int=7
class TrattamentoImport(BaseModel):
    nome: str; area: str; prezzo: float

# --- FUNZIONE STAMPA (AGGIUNTA PER RISOLVERE ERRORE 404) ---
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
            righe_html += f"<tr><td style='border-bottom:1px solid #ddd; padding:8px;'>{nome}</td><td style='border-bottom:1px solid #ddd; padding:8px; text-align:center;'>{riga.quantita}</td><td style='border-bottom:1px solid #ddd; padding:8px; text-align:right;'>€ {sub:.2f}</td></tr>"

        html = f"""
        <html><body style="font-family:Arial; padding:40px; max-width:800px; margin:auto;">
            <div style="text-align:center; margin-bottom:40px;">
                <h1>FOCUS REHAB</h1>
                <p>Preventivo di Riabilitazione</p>
            </div>
            <p><strong>Paziente:</strong> {prev.paziente_rel.cognome} {prev.paziente_rel.nome}</p>
            <p><strong>Data:</strong> {prev.data_creazione} &nbsp;&nbsp; <strong>Oggetto:</strong> {prev.oggetto}</p>
            <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                <tr style="background:#eee;">
                    <th style="padding:10px; text-align:left;">Descrizione</th>
                    <th style="padding:10px;">Q.tà</th>
                    <th style="padding:10px; text-align:right;">Importo</th>
                </tr>
                {righe_html}
            </table>
            <h3 style="text-align:right; margin-top:30px;">TOTALE: € {totale:.2f}</h3>
            <p style="margin-top:20px; font-size:0.9em; color:#555;">Note: {prev.note if prev.note else ''}</p>
            <div style="text-align:center; margin-top:50px;">
                <button onclick="window.print()" style="padding:10px 20px; font-size:16px;">🖨️ STAMPA ADESSO</button>
            </div>
        </body></html>
        """
        return html

# --- AZIONI RAPIDE ---
@app.get("/magazzino/piu/{pk}")
def aumenta_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item:
            item.quantita += 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

@app.get("/magazzino/meno/{pk}")
def diminuisci_quantita(request: Request, pk: int):
    with Session(engine) as session:
        item = session.get(Inventario, pk)
        if item and item.quantita > 0:
            item.quantita -= 1; session.add(item); session.commit()
    return RedirectResponse(request.url_for("admin:list", identity="inventario"), status_code=303)

# --- 1. PAZIENTI (TUO CODICE) ---
class PazienteAdmin(ModelView, model=Paziente):
    name = "Paziente"; name_plural = "Pazienti"; icon = "fa-solid fa-user-injured"
    column_formatters = {
        Paziente.disdetto: lambda m, a: "✅" if m.disdetto else "",
        Paziente.visita_medica: lambda m, a: "🩺" if m.visita_medica else ""
    }
    column_list = [Paziente.cognome, Paziente.nome, Paziente.area, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto]
    column_searchable_list = [Paziente.cognome, Paziente.nome]
    form_columns = [Paziente.nome, Paziente.cognome, Paziente.area, Paziente.note, Paziente.visita_medica, Paziente.data_visita, Paziente.disdetto, Paziente.data_disdetta]
    @action(name="segna_disdetto", label="❌ Segna Disdetto", confirmation_message="Confermi?")
    def action_disdetto(self, request: Request):
        pks = request.query_params.get("pks", "").split(",")
        with self.session_maker() as session:
            for pk in pks:
                if pk.isdigit():
                    model = session.get(Paziente, int(pk))
                    if model: model.disdetto = True; model.data_disdetta = date.today(); session.add(model)
            session.commit()
        return RedirectResponse(request.url_for("admin:list", identity="paziente"), status_code=303)

# --- 2. MAGAZZINO (TUO CODICE) ---
class InventarioAdmin(ModelView, model=Inventario):
    name = "Articolo"; name_plural = "Magazzino"; icon = "fa-solid fa-box"
    def formatta_con_bottoni(model, attribute):
        stato = ""
        if model.quantita <= model.soglia_minima: stato = f"🔴 {model.quantita} (ORDINA!)"
        elif model.quantita >= model.obiettivo: stato = f"🌟 {model.quantita} (Pieno)"
        else: stato = f"✅ {model.quantita} (Ok)"
        style = "text-decoration:none; border:1px solid #ccc; padding:2px 6px; border-radius:4px; margin:0 2px; background:#f9f9f9;"
        btn_meno = f'<a href="/magazzino/meno/{model.id}" style="{style}">➖</a>'
        btn_piu = f'<a href="/magazzino/piu/{model.id}" style="{style}">➕</a>'
        return Markup(f"{btn_meno} &nbsp; <b>{stato}</b> &nbsp; {btn_piu}")
    column_formatters = {Inventario.quantita: formatta_con_bottoni}
    column_list = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]
    form_columns = [Inventario.materiale, Inventario.area_stanza, Inventario.quantita, Inventario.soglia_minima, Inventario.obiettivo]

# --- 3. PRESTITI (TUO CODICE) ---
class PrestitoAdmin(ModelView, model=Prestito):
    name = "Prestito"; name_plural = "Prestiti"; icon = "fa-solid fa-stopwatch"
    def list_query(self, request): return select(Prestito).where(Prestito.restituito == False)
    def formatta_scadenza(model, attribute):
        if not model.data_scadenza: return "⏳ In corso"
        diff = (model.data_scadenza - date.today()).days
        if diff < 0: return Markup(f'<span style="color:red; font-weight:bold;">🔴 SCADUTO da {abs(diff)} gg!</span>')
        return Markup(f"⏳ Scade tra {diff} gg")
    column_formatters = {Prestito.data_scadenza: formatta_scadenza}
    column_list = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_scadenza]
    form_columns = [Prestito.area, Prestito.oggetto, Prestito.paziente, Prestito.data_inizio, Prestito.durata_giorni, Prestito.restituito]
    async def on_model_change(self, data, model, is_created, request):
        if model.data_inizio and model.durata_giorni: model.data_scadenza = model.data_inizio + timedelta(days=model.durata_giorni)

# --- 4. LISTINO PREZZI (RIATTIVATO PER I PREVENTIVI) ---
class TrattamentoAdmin(ModelView, model=Trattamento):
    name = "Listino Prezzi"
    name_plural = "Listino Prezzi"
    icon = "fa-solid fa-tags"
    column_list = [Trattamento.nome, Trattamento.prezzo_base]
    form_columns = [Trattamento.nome, Trattamento.area, Trattamento.prezzo_base]

# --- 5. PREVENTIVI (FUNZIONANTE E CON STAMPA) ---
class RigaPreventivoInline(ModelView, model=RigaPreventivo):
    column_list = [RigaPreventivo.trattamento, RigaPreventivo.quantita, RigaPreventivo.sconto]

class PreventivoAdmin(ModelView, model=Preventivo):
    name = "Preventivo"
    name_plural = "Preventivi"
    icon = "fa-solid fa-file-invoice-dollar"
    
    inlines = [RigaPreventivoInline] # Questo abilita la spesa

    def link_stampa(model, attribute):
        return Markup(f'<a href="/stampa_preventivo/{model.id}" target="_blank" style="font-size:1.2em;">🖨️ STAMPA</a>')

    column_formatters = {Preventivo.id: link_stampa}
    column_list = [Preventivo.id, Preventivo.data_creazione, Preventivo.paziente_rel, Preventivo.totale_calcolato]
    form_columns = [Preventivo.paziente_rel, Preventivo.data_creazione, Preventivo.oggetto, Preventivo.note, Preventivo.accettato]

    async def after_model_change(self, data, model, is_created, request):
        with Session(engine) as session:
            stmt = select(Preventivo).where(Preventivo.id == model.id)
            prev = session.exec(stmt).first()
            if prev and prev.righe:
                tot = 0
                for riga in prev.righe:
                    if riga.trattamento:
                        tot += (riga.trattamento.prezzo_base * riga.quantita) - riga.sconto
                prev.totale_calcolato = tot
                session.add(prev); session.commit()

# 6. SCADENZE
class ScadenzaAdmin(ModelView, model=Scadenza):
    name="Scadenza"; name_plural="Scadenzario"; icon="fa-solid fa-calendar"
    column_list=[Scadenza.descrizione, Scadenza.data_scadenza, Scadenza.importo]

# --- ATTIVAZIONE ---
admin = Admin(app, engine)
admin.add_view(PazienteAdmin)
admin.add_view(InventarioAdmin)
admin.add_view(PrestitoAdmin)
admin.add_view(TrattamentoAdmin) # Riattivato
admin.add_view(PreventivoAdmin)
admin.add_view(ScadenzaAdmin)

@app.on_event("startup")
def on_startup(): init_db()

# --- IMPORTATORI (I TUOI ORIGINALI) ---
@app.post("/import-rapido")
def import_pazienti(l: List[PazienteImport]):
    with Session(engine) as s:
        for p in l: s.add(Paziente(nome=p.nome, cognome=p.cognome, area=p.area))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-magazzino")
def import_magazzino(l: List[InventarioImport]):
    with Session(engine) as s:
        for i in l: s.add(Inventario(materiale=i.materiale, area_stanza=i.area_stanza, quantita=i.quantita, soglia_minima=i.soglia_minima, obiettivo=i.obiettivo))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-prestiti")
def import_prestiti(l: List[PrestitoImport]):
    with Session(engine) as s:
        for i in l:
            p = s.exec(select(Paziente).where(Paziente.nome==i.nome_paziente, Paziente.cognome==i.cognome_paziente)).first()
            s.add(Prestito(oggetto=i.oggetto, area=i.area, paziente_id=p.id if p else None, durata_giorni=i.durata_giorni))
        s.commit()
    return {"msg": "Ok"}
@app.post("/import-trattamenti")
def import_trattamenti(l: List[TrattamentoImport]):
    with Session(engine) as s:
        for i in l: s.add(Trattamento(nome=i.nome, area=i.area, prezzo_base=i.prezzo))
        s.commit()
    return {"msg": "Ok"}
