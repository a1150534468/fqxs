"""WebSocket router for streaming setting generation.

Protocol:
  Client → Server (JSON):
    {
      "action": "generate",
      "token": "<jwt access token>",
      "setting_type": "worldview",
      "book_title": "...",
      "genre": "...",
      "context": "...",
      "prior_settings": [...]
    }

  Server → Client (JSON, multiple):
    {"type": "chunk", "content": "文字片段"}        # repeated
    {"type": "done", "setting_type": "...", ...}    # final
    {"type": "error", "message": "..."}             # on error
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from services.llm_client import llm_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Generation"])


async def _safe_send(websocket: WebSocket, data: dict) -> bool:
    """Send JSON to WebSocket, returning False if the connection is gone."""
    try:
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        await websocket.send_json(data)
        return True
    except (WebSocketDisconnect, RuntimeError):
        return False


@router.websocket("/ws/generate-setting")
async def ws_generate_setting(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()

            if payload.get("action") != "generate":
                await _safe_send(websocket, {
                    "type": "error",
                    "message": f"Unknown action: {payload.get('action')}",
                })
                continue

            setting_type = payload.get("setting_type", "")
            if not setting_type:
                await _safe_send(websocket, {
                    "type": "error",
                    "message": "setting_type is required",
                })
                continue

            token = payload.get("token") or None
            book_title = payload.get("book_title", "")
            genre = payload.get("genre", "")
            context = payload.get("context", "")
            prior_settings = payload.get("prior_settings") or []

            logger.info(
                f"WS generate-setting: type={setting_type}, book={book_title}, "
                f"has_token={bool(token)}"
            )

            try:
                async for kind, data in llm_client.generate_setting_stream(
                    setting_type=setting_type,
                    book_title=book_title,
                    genre=genre,
                    context=context,
                    prior_settings=prior_settings,
                    user_token=token,
                ):
                    if kind == "chunk":
                        if not await _safe_send(websocket, {
                            "type": "chunk",
                            "content": data,
                        }):
                            logger.info("WS client gone during streaming, stopping")
                            return
                    elif kind == "done":
                        await _safe_send(websocket, {
                            "type": "done",
                            **data,
                        })
            except Exception as e:
                logger.exception(f"WS generate-setting failed: {e}")
                await _safe_send(websocket, {
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    except Exception as e:
        logger.exception(f"WS unexpected error: {e}")
        await _safe_send(websocket, {"type": "error", "message": str(e)})
