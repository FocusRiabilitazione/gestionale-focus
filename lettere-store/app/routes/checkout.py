import os
import stripe
import httpx
import base64
import json
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pydantic import BaseModel

from ..database import get_session
from ..models import Ordine, ColoreDisponibile, StatoOrdine, MetodoPagamento, TipoEvento, Dimensione

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PREZZI = {
    "Piccola (15cm)": 22.0,
    "Media (20cm)": 30.0,
    "Grande (30cm)": 45.0,
}

# ─── PAYPAL HELPERS ──────────────────────────────────────────────────────────

def _paypal_base_url():
    mode = os.getenv("PAYPAL_MODE", "sandbox")
    return "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"


async def _paypal_access_token() -> str:
    client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
    credentials = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_paypal_base_url()}/v1/oauth2/token",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            data="grant_type=client_credentials",
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


# ─── CREA ORDINE (form step 1→2) ─────────────────────────────────────────────

class OrdineData(BaseModel):
    nome: str
    cognome: str
    email: str
    telefono: str = ""
    lettera_iniziale: str
    nome_personalizzato: str
    colore_nome: str = ""
    colore_hex: str = ""
    dimensione: str
    tipo_evento: str
    note_cliente: str = ""
    indirizzo: str
    citta: str
    cap: str
    provincia: str
    metodo_pagamento: str


@router.post("/checkout/crea-ordine")
async def crea_ordine(data: OrdineData, session: Session = Depends(get_session)):
    prezzo = PREZZI.get(data.dimensione, 30.0)

    ordine = Ordine(
        nome=data.nome,
        cognome=data.cognome,
        email=data.email,
        telefono=data.telefono,
        lettera_iniziale=data.lettera_iniziale.upper(),
        nome_personalizzato=data.nome_personalizzato,
        colore_nome=data.colore_nome,
        colore_hex=data.colore_hex,
        dimensione=Dimensione(data.dimensione),
        tipo_evento=TipoEvento(data.tipo_evento),
        note_cliente=data.note_cliente,
        indirizzo=data.indirizzo,
        citta=data.citta,
        cap=data.cap,
        provincia=data.provincia,
        prezzo_unitario=prezzo,
        totale=prezzo,
        metodo_pagamento=MetodoPagamento(data.metodo_pagamento),
    )
    session.add(ordine)
    session.commit()
    session.refresh(ordine)
    return {"ordine_id": ordine.id, "codice": ordine.codice_ordine, "totale": ordine.totale}


# ─── STRIPE ──────────────────────────────────────────────────────────────────

@router.post("/checkout/stripe/sessione")
async def crea_sessione_stripe(request: Request, session: Session = Depends(get_session)):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    body = await request.json()
    ordine_id = body.get("ordine_id")

    ordine = session.get(Ordine, ordine_id)
    if not ordine:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Lettera '{ordine.lettera_iniziale}' con nome '{ordine.nome_personalizzato}'",
                    "description": f"{ordine.dimensione} – {ordine.tipo_evento}",
                },
                "unit_amount": int(ordine.totale * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=ordine.email,
        success_url=f"{base_url}/ordine/successo/{ordine.codice_ordine}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/ordina",
        metadata={"ordine_id": str(ordine.id), "codice": ordine.codice_ordine},
    )
    return {"checkout_url": checkout_session.url}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook non valido")

    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]
        ordine_id = int(data["metadata"].get("ordine_id", 0))
        ordine = session.get(Ordine, ordine_id)
        if ordine:
            ordine.stato = StatoOrdine.PAGATO
            ordine.pagamento_completato = True
            ordine.pagamento_id = data["id"]
            ordine.data_aggiornamento = datetime.utcnow()
            session.add(ordine)
            session.commit()

    return {"ok": True}


# ─── PAYPAL ──────────────────────────────────────────────────────────────────

@router.post("/checkout/paypal/crea-ordine")
async def paypal_crea_ordine(request: Request, session: Session = Depends(get_session)):
    body = await request.json()
    ordine_id = body.get("ordine_id")
    ordine = session.get(Ordine, ordine_id)
    if not ordine:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    token = await _paypal_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_paypal_base_url()}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "EUR", "value": f"{ordine.totale:.2f}"},
                    "description": f"Lettera '{ordine.lettera_iniziale}' – {ordine.nome_personalizzato}",
                    "custom_id": str(ordine.id),
                }],
            },
        )
        resp.raise_for_status()
        pp_order = resp.json()

    return {"paypal_order_id": pp_order["id"]}


@router.post("/checkout/paypal/cattura")
async def paypal_cattura(request: Request, session: Session = Depends(get_session)):
    body = await request.json()
    paypal_order_id = body.get("paypal_order_id")
    ordine_id = body.get("ordine_id")

    token = await _paypal_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_paypal_base_url()}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        capture = resp.json()

    if capture.get("status") == "COMPLETED":
        ordine = session.get(Ordine, ordine_id)
        if ordine:
            ordine.stato = StatoOrdine.PAGATO
            ordine.pagamento_completato = True
            ordine.pagamento_id = paypal_order_id
            ordine.data_aggiornamento = datetime.utcnow()
            session.add(ordine)
            session.commit()
        return {"success": True, "codice": ordine.codice_ordine if ordine else ""}

    raise HTTPException(status_code=400, detail="Pagamento non completato")


# ─── PAGINA CONFERMA ─────────────────────────────────────────────────────────

@router.get("/ordine/successo/{codice}", response_class=HTMLResponse)
def pagina_successo(codice: str, request: Request, session: Session = Depends(get_session)):
    ordine = session.exec(select(Ordine).where(Ordine.codice_ordine == codice)).first()
    if not ordine:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    # Segna come pagato se arriva da Stripe redirect (verifica session_id opzionale)
    if not ordine.pagamento_completato:
        session_id = request.query_params.get("session_id")
        if session_id:
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            try:
                cs = stripe.checkout.Session.retrieve(session_id)
                if cs.payment_status == "paid":
                    ordine.stato = StatoOrdine.PAGATO
                    ordine.pagamento_completato = True
                    ordine.pagamento_id = session_id
                    ordine.data_aggiornamento = datetime.utcnow()
                    session.add(ordine)
                    session.commit()
            except Exception:
                pass

    return templates.TemplateResponse(request, "conferma.html", {
        "ordine": ordine,
    })
