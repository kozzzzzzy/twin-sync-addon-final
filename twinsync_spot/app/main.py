"""TwinSync Spot - Main FastAPI Application."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db.sqlite import Database
from app.api.routes import router as api_router


# Get configuration from environment
INGRESS_PATH = os.environ.get("INGRESS_PATH", "")
DATA_DIR = os.environ.get("DATA_DIR", "/data")

# Paths
APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "web" / "static"
TEMPLATES_DIR = APP_DIR / "web" / "templates"

# Database instance
db: Database = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    global db
    
    # Startup
    db_path = Path(DATA_DIR) / "twinsync.db"
    db = Database(str(db_path))
    await db.init()
    
    # Store db in app state for access in routes
    app.state.db = db
    app.state.ingress_path = INGRESS_PATH
    
    yield
    
    # Shutdown
    await db.close()


# Create FastAPI app
app = FastAPI(
    title="TwinSync Spot",
    description="Does this match YOUR definition?",
    version="1.0.1",
    lifespan=lifespan,
    docs_url=f"{INGRESS_PATH}/docs" if INGRESS_PATH else "/docs",
    openapi_url=f"{INGRESS_PATH}/openapi.json" if INGRESS_PATH else "/openapi.json",
)

# Mount static files
app.mount(
    f"{INGRESS_PATH}/static" if INGRESS_PATH else "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Include API routes
app.include_router(api_router, prefix=f"{INGRESS_PATH}/api" if INGRESS_PATH else "/api")


@app.get(f"{INGRESS_PATH}/" if INGRESS_PATH else "/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "ingress_path": INGRESS_PATH,
        }
    )


@app.get(f"{INGRESS_PATH}/add" if INGRESS_PATH else "/add", response_class=HTMLResponse)
async def add_spot_page(request: Request):
    """Add spot page."""
    return templates.TemplateResponse(
        "add_spot.html",
        {
            "request": request,
            "ingress_path": INGRESS_PATH,
        }
    )


@app.get(f"{INGRESS_PATH}/spot/{{spot_id}}" if INGRESS_PATH else "/spot/{spot_id}", response_class=HTMLResponse)
async def spot_detail_page(request: Request, spot_id: int):
    """Spot detail page."""
    return templates.TemplateResponse(
        "spot_detail.html",
        {
            "request": request,
            "spot_id": spot_id,
            "ingress_path": INGRESS_PATH,
        }
    )


@app.get(f"{INGRESS_PATH}/settings" if INGRESS_PATH else "/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    has_key = bool(gemini_key and len(gemini_key) > 10)
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "ingress_path": INGRESS_PATH,
            "has_api_key": has_key,
            "mode": "addon" if os.environ.get("SUPERVISOR_TOKEN") else "standalone",
        }
    )
