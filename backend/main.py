import os
import sys
from pathlib import Path

# Ensure root directory is always in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.models import District
from backend.api.routes import router as api_router
from backend.services.scheduler import scheduler_instance

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ushna.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    # Startup: Create tables and initialize districts so schema is immediately ready
    logger.info("Initializing Ushna Kaappaan database schema...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        scheduler_instance.initialize_districts(db)
        logger.info("Districts initialized. Dispatching initial ingestion to background thread...")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}", exc_info=True)
    finally:
        db.close()
        
    # Run initial ingestion asynchronously in background so server port binds immediately
    asyncio.create_task(asyncio.to_thread(scheduler_instance.run_full_pipeline, settings.APP_MODE))
        
    yield
    logger.info("Shutting down Ushna Kaappaan server.")

app = FastAPI(
    title=settings.FULL_TITLE,
    description="Scientific UTCI human thermal stress calculation and state mortality risk early warning platform for South India.",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Mount GeoJSON static data
static_data_path = settings.DATA_DIR
if static_data_path.exists():
    app.mount("/data", StaticFiles(directory=str(static_data_path)), name="data")

# Frontend static files if built (optional)
frontend_dist_path = settings.BASE_DIR / "frontend" / "dist"
assets_path = frontend_dist_path / "assets"
index_path = frontend_dist_path / "index.html"
if frontend_dist_path.exists() and assets_path.exists() and index_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = frontend_dist_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(index_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
