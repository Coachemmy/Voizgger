import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.db import add_invoice, delete_all_invoices, list_invoices
from app.core.limits import rate_limit, reserve_ai_call
from app.services.meta_ai import process_voice_to_ledger, translate_ledger, verify_inventory

router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac", ".aac", ".mp4", ".mpeg", ".mpga"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class TranslateRequest(BaseModel):
    transcript: str = ""
    items: list = []
    summary: str = ""
    follow_up_sms: str = ""
    language: str = "English"


class InvoiceRequest(BaseModel):
    id: str
    date: str = ""
    summary: str = ""
    items: list = []
    quantity: list = []
    amount_paid: float = 0
    amount_owed: float = 0


@router.get("/invoices")
async def get_invoices():
    return JSONResponse(content=list_invoices())


@router.post("/invoices")
async def create_invoice(payload: InvoiceRequest):
    if not payload.id.strip():
        return JSONResponse(status_code=400, content={"error": "Invoice id is required."})
    add_invoice(payload.model_dump())
    return JSONResponse(content=list_invoices())


@router.delete("/invoices")
async def clear_invoices():
    delete_all_invoices()
    return JSONResponse(content=[])


@router.post("/analyze_voice", dependencies=[Depends(rate_limit)])
async def analyze_voice(
    file: UploadFile = File(...),
    language: str = Form("English"),
    deep_audit: bool = Form(False),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in AUDIO_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"error": "Unsupported audio format. Please upload MP3, WAV, M4A, WEBM or OGG."},
        )

    contents = await file.read()
    if not contents:
        return JSONResponse(status_code=400, content={"error": "That file is empty. Please try another recording."})
    if len(contents) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={"error": "File is too large. Please keep recordings under 25 MB."},
        )

    reserve_ai_call()
    result = process_voice_to_ledger(
        contents,
        file.filename,
        language=language[:40],
        deep_audit=deep_audit,
    )
    return JSONResponse(content=result)


@router.post("/translate", dependencies=[Depends(rate_limit)])
async def translate(payload: TranslateRequest):
    reserve_ai_call()
    result = translate_ledger(
        payload.transcript,
        payload.items,
        payload.summary,
        payload.follow_up_sms,
        payload.language[:40],
    )
    return JSONResponse(content=result)


@router.post("/verify_stock", dependencies=[Depends(rate_limit)])
async def verify_stock(
    file: UploadFile = File(...),
    items: str = Form("[]"),
    quantities: str = Form("[]"),
):
    try:
        item_list = json.loads(items)
        quantity_list = json.loads(quantities)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid items payload."})

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"error": "Unsupported image format. Please upload JPG, PNG or WEBP."},
        )

    contents = await file.read()
    if not contents:
        return JSONResponse(status_code=400, content={"error": "That image is empty. Please try another photo."})
    if len(contents) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={"error": "Image is too large. Please keep photos under 25 MB."},
        )

    reserve_ai_call()
    result = verify_inventory(contents, file.content_type, item_list, quantity_list)
    return JSONResponse(content=result)
