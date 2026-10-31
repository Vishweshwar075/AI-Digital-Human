
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router

app = FastAPI(
    title="Project EVA AI Service",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "null",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Project EVA AI Service is running"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EVA AI Service",
        "version": "1.0"
    }
