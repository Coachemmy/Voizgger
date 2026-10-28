from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from app.services.meta_ai import process_voice_to_ledger

router = APIRouter()

@router.post("/analyze_voice")
async def analyze_voice(file: UploadFile = File(...)):
    contents = await file.read()
    result = process_voice_to_ledger(contents, file.filename)
    return JSONResponse(content=result)