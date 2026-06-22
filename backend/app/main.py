from fastapi import FastAPI

from app.api.health import router

app = FastAPI(
    title="RoboCutter API",
    version="1.1.0"
)

app.include_router(router)

@app.get("/")
def root():

    return {
        "application": "RoboCutter",
        "status": "running"
    }