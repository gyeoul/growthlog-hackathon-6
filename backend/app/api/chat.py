import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.schemas import ChatRequest, ChatResponse
from app.services import llm

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, settings: Settings = Depends(get_settings)
) -> ChatResponse:
    try:
        content = await llm.complete(settings, body.messages)
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(content=content, model=settings.llm_model)


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest, settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    """Server-Sent Events: `data: {"delta": "..."}` then `data: [DONE]`."""

    async def events() -> AsyncIterator[str]:
        try:
            async for delta in llm.stream(settings, body.messages):
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except llm.LLMError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
