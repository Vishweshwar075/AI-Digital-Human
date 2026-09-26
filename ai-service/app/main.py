from fastapi import FastAPI
from app.routes.chat import router



app = FastAPI(
    title="Project EVA AI Service",
    version="1.0"
)

app.include_router(router)
@app.get("/")
def home():
    return {
        "message": "Project EVA AI Service is Running 🚀"
    }