import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import resumes

from dotenv import load_dotenv
load_dotenv()

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app = FastAPI(title="AI Job Tracker API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router)

@app.get("/health")
def health():
    return {"status": "ok"}


