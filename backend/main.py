from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root():
    payload = {
        "status": "online",
        "version": "0.0.2",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": "Hello from FastAPI!",
    }
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store"},
    )
