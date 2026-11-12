import hmac
import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from a2wsgi import WSGIMiddleware

from app import app as flask_app


api = FastAPI(
    title="Mahliyo AI API",
    description="Chat, image generation, and video generation API.",
    version="1.0.0",
)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    history: list[dict[str, Any]] = Field(default_factory=list)
    system_prompt: str | None = None
    use_search: bool = False
    image: dict[str, str] | None = None


class GenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)


def require_api_key(provided_key: str | None = Security(api_key_header)) -> None:
    configured_key = os.getenv("MAHLIYO_API_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="API yopiq. Server .env faylida MAHLIYO_API_KEY ni sozlang.",
        )
    if not provided_key or not hmac.compare_digest(provided_key, configured_key):
        raise HTTPException(status_code=401, detail="X-API-Key noto'g'ri yoki berilmagan.")


def forward_to_flask(path: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    with flask_app.test_client() as client:
        if payload is None:
            response = client.get(path)
        else:
            response = client.post(path, json=payload)
    result = response.get_json(silent=True)
    if result is None:
        result = {"error": response.get_data(as_text=True)}
    return JSONResponse(content=result, status_code=response.status_code)


@api.get("/v1/health", tags=["system"])
def health() -> JSONResponse:
    return forward_to_flask("/api/health")


@api.post("/v1/chat", tags=["chat"], dependencies=[Depends(require_api_key)])
def chat(body: ChatRequest) -> JSONResponse:
    return forward_to_flask("/api/chat", body.model_dump(exclude_none=True))


@api.post("/v1/generate/image", tags=["generation"], dependencies=[Depends(require_api_key)])
def generate_image(body: GenerationRequest) -> JSONResponse:
    return forward_to_flask("/api/chat", {"message": f"Rasm yarat: {body.prompt}"})


@api.post("/v1/generate/video", tags=["generation"], dependencies=[Depends(require_api_key)])
def generate_video(body: GenerationRequest) -> JSONResponse:
    return forward_to_flask("/api/chat", {"message": f"Video yarat: {body.prompt}"})


api.mount("/", WSGIMiddleware(flask_app))