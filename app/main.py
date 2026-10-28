from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.endpoints import router as api_router

app = FastAPI(title="VoxLedger API", description="Voice-to-Ledger for Informal Economy")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(api_router, prefix="/api")

@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")