from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base
from app.routers.auth_router import router as auth_router
from app.routers.cars_router import router as cars_router
from app.scraper.scraper import run_scraper
from app.seed import seed_admin

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

    scheduler.add_job(
        run_scraper,
        "interval",
        minutes=settings.SCRAPE_INTERVAL_MINUTES,
        id="scraper_job",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[app] Scraper scheduled every {settings.SCRAPE_INTERVAL_MINUTES} minutes")

    # Run scraper once on startup
    scheduler.add_job(run_scraper, id="scraper_initial", replace_existing=True)

    yield

    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(title="CarSensor Listings API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(cars_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
