from fastapi import FastAPI
from database import engine, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Арена переговоров")


@app.get("/health")
def health():
    return {"status": "ok"}