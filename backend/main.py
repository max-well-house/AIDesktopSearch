from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from capabilities import build_capabilities
from capabilities.schema import HealthResponse

APP_VERSION = "0.0.3"

app = FastAPI(title="AI Desktop Search API", version=APP_VERSION)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _health_payload() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        timestamp=_utc_timestamp(),
        capabilities=await build_capabilities(),
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    payload = await _health_payload()
    return JSONResponse(
        content=payload.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/")
async def root():
    """Compatibility shim — same healthy capability payload as /health."""
    payload = await _health_payload()
    return JSONResponse(
        content=payload.model_dump(),
        headers={"Cache-Control": "no-store"},
    )
