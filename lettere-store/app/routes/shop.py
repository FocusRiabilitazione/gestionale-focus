from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..database import get_session
from ..models import ColoreDisponibile, ConfigSito

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


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, session: Session = Depends(get_session)):
    colori = session.exec(
        select(ColoreDisponibile)
        .where(ColoreDisponibile.disponibile == True)
        .order_by(ColoreDisponibile.ordine_visualizzazione)
    ).all()
    config = get_config(session)
    return templates.TemplateResponse(request, "index.html", {
        "colori": colori,
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
    config = get_config(session)
    import os
    return templates.TemplateResponse(request, "ordina.html", {
        "colori": colori,
        "prezzi": PREZZI,
        "config": config,
        "paypal_client_id": os.getenv("PAYPAL_CLIENT_ID", ""),
        "stripe_pk": os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
    })
