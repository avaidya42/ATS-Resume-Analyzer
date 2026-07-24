from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import resume

app = FastAPI(title="Resume Intelligence Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
