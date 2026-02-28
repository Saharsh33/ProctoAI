from fastapi import FastAPI
from app.routers import auth, exam

app = FastAPI(title="ProctoAI Backend")

app.include_router(auth.router)
app.include_router(exam.router)

@app.get("/")
def health():
    return {"status": "running"}