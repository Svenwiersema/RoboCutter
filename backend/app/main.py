from fastapi import FastAPI

app = FastAPI(
    title="RoboCutter API",
    version="1.1.0"
)


@app.get("/")
def root():

    return {
        "application": "RoboCutter",
        "status": "running"
    }