from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import locations

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(locations.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "AroundMe Agent API"}