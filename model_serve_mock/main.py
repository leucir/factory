"""OpenAI-compatible FastAPI service that mocks model serving responses."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


class CompletionRequest(BaseModel):
    """Request payload for generating a text completion (OpenAI format)."""

    model: str = Field(..., description="Model to use for completion")
    prompt: str = Field(..., description="Input prompt for the model")
    max_tokens: int = Field(16, ge=1, le=512, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")


class CompletionChoice(BaseModel):
    """Individual completion choice (OpenAI format)."""
    
    text: str
    index: int
    logprobs: Optional[dict] = None
    finish_reason: str = "stop"


class CompletionUsage(BaseModel):
    """Token usage information (OpenAI format)."""
    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResponse(BaseModel):
    """Response payload containing the generated text (OpenAI format)."""

    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: CompletionUsage


class ChatMessage(BaseModel):
    """Chat message (OpenAI format)."""
    
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request payload for chat completions (OpenAI format)."""

    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    max_tokens: int = Field(16, ge=1, le=512, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")


class ChatChoice(BaseModel):
    """Individual chat choice (OpenAI format)."""
    
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    """Response payload for chat completions (OpenAI format)."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: CompletionUsage


app = FastAPI(title="LLM Factory Prototype", version="0.1.0")


@app.get("/healthz", tags=["system"])
def healthcheck() -> dict:
    """Return basic health information."""

    return {
        "status": "ok",
        "service": "llm-factory",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/v1/completions", response_model=CompletionResponse, tags=["inference"])
def generate_completion(request: CompletionRequest) -> CompletionResponse:
    """Return a deterministic stub completion for the prototype (OpenAI format)."""

    completion_text = f"Echo: {request.prompt.strip()}"
    prompt_tokens = len(request.prompt.split())
    completion_tokens = min(prompt_tokens + 1, request.max_tokens)
    
    return CompletionResponse(
        id=f"cmpl-{uuid.uuid4().hex[:8]}",
        created=int(datetime.utcnow().timestamp()),
        model=request.model,
        choices=[
            CompletionChoice(
                text=completion_text,
                index=0,
                finish_reason="stop"
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse, tags=["inference"])
def generate_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Return a deterministic stub chat completion for the prototype (OpenAI format)."""

    # Extract the last user message
    last_message = None
    for message in reversed(request.messages):
        if message.role == "user":
            last_message = message
            break
    
    if not last_message:
        last_message = ChatMessage(role="user", content="Hello")
    
    completion_text = f"Echo: {last_message.content.strip()}"
    prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
    completion_tokens = min(prompt_tokens + 1, request.max_tokens)
    
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(datetime.utcnow().timestamp()),
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=completion_text),
                finish_reason="stop"
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )


if __name__ == "__main__":  # pragma: no cover - convenience for local runs
    import uvicorn

    uvicorn.run("model_serve_mock.main:app", host="0.0.0.0", port=8080, reload=False)
