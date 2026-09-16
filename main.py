from fastapi import FastAPI

app = FastAPI(title="Арена переговоров")

@app.get("/health")
def health():
    return {"status": "ok"}