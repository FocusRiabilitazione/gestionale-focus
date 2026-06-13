import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..database import get_session
from ..models import ColoreDisponibile, ConfigSito, Tema, ElementoTema

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PREZZI = {
    "Piccola (15cm)": 22.0,
    "Media (20cm)": 30.0,
    "Grande (30cm)": 45.0,
}


def get_config(session: Session) -> dict:
    rows = session.exec(select(ConfigSito)).all()
    return {r.chiave: r.valore for r in rows}


def get_temi_json(session: Session) -> list:
    """Restituisce tutti i temi con i loro elementi come lista di dizionari (per Alpine.js)."""
    temi = session.exec(
        select(Tema)
        .where(Tema.disponibile == True)
        .order_by(Tema.ordine_visualizzazione)
    ).all()
    result = []
    for tema in temi:
        elementi = session.exec(
            select(ElementoTema)
            .where(ElementoTema.tema_id == tema.id, ElementoTema.disponibile == True)
        ).all()
        result.append({
            "id": tema.id,
            "nome": tema.nome,
            "emoji": tema.emoji,
            "descrizione": tema.descrizione or "",
            "elementi": [
                {"id": e.id, "nome": e.nome, "emoji": e.emoji, "prezzo": e.prezzo_aggiuntivo}
                for e in elementi
            ],
        })
    return result


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, session: Session = Depends(get_session)):
    colori = session.exec(
        select(ColoreDisponibile)
        .where(ColoreDisponibile.disponibile == True)
        .order_by(ColoreDisponibile.ordine_visualizzazione)
    ).all()
    temi = session.exec(
        select(Tema).where(Tema.disponibile == True).order_by(Tema.ordine_visualizzazione)
    ).all()
    config = get_config(session)
    return templates.TemplateResponse(request, "index.html", {
        "colori": colori,
        "temi": temi,
        "prezzi": PREZZI,
        "config": config,
    })


@router.get("/ordina", response_class=HTMLResponse)
def pagina_ordina(request: Request, session: Session = Depends(get_session)):
    colori = session.exec(
        select(ColoreDisponibile)
        .where(ColoreDisponibile.disponibile == True)
        .order_by(ColoreDisponibile.ordine_visualizzazione)
    ).all()
    temi_json = get_temi_json(session)
    config = get_config(session)
    return templates.TemplateResponse(request, "ordina.html", {
        "colori": colori,
        "temi_json": temi_json,
        "prezzi": PREZZI,
        "config": config,
        "paypal_client_id": os.getenv("PAYPAL_CLIENT_ID", ""),
        "stripe_pk": os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
    })
