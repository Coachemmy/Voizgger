from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.endpoints import router as api_router
from app.core.limits import LimitExceeded

app = FastAPI(title="Voizgger API", description="Voice-to-Ledger for Informal Economy")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(api_router, prefix="/api")


@app.exception_handler(LimitExceeded)
async def limit_exceeded_handler(request: Request, exc: LimitExceeded):
    return JSONResponse(status_code=429, content={"error": exc.message})


@app.get("/health")
async def health():
    """Cheap probe for uptime pingers: no database, no model call."""
    return {"status": "ok"}


@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
