from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base, SessionLocal
import models
from routers import admin, negotiation
from seed_data import seed_scenarios

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    seed_scenarios(db, models)
finally:
    db.close()

app = FastAPI(title="Арена переговоров")

app.include_router(admin.router)
app.include_router(negotiation.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/admin")
def admin_page():
    return FileResponse("static/admin.html")