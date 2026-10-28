import json

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.meta_ai import process_voice_to_ledger, translate_ledger, verify_inventory

router = APIRouter()


class TranslateRequest(BaseModel):
    transcript: str = ""
    items: list = []
    summary: str = ""
    follow_up_sms: str = ""
    language: str = "English"


@router.post("/analyze_voice")
async def analyze_voice(
    file: UploadFile = File(...),
    language: str = Form("English"),
    deep_audit: bool = Form(False),
):
    contents = await file.read()
    result = process_voice_to_ledger(
        contents,
        file.filename,
        language=language[:40],
        deep_audit=deep_audit,
    )
    return JSONResponse(content=result)


@router.post("/translate")
async def translate(payload: TranslateRequest):
    result = translate_ledger(
        payload.transcript,
        payload.items,
        payload.summary,
        payload.follow_up_sms,
        payload.language[:40],
    )
    return JSONResponse(content=result)


@router.post("/verify_stock")
async def verify_stock(
    file: UploadFile = File(...),
    items: str = Form("[]"),
    quantities: str = Form("[]"),
):
    try:
        item_list = json.loads(items)
        quantity_list = json.loads(quantities)
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Invalid items payload."})

    contents = await file.read()
    result = verify_inventory(contents, file.content_type, item_list, quantity_list)
    return JSONResponse(content=result)
