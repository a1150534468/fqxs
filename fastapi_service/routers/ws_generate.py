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

from services.llm_client import llm_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Generation"])


@router.websocket("/ws/generate-setting")
async def ws_generate_setting(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()

            if payload.get("action") != "generate":
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {payload.get('action')}",
                })
                continue

            setting_type = payload.get("setting_type", "")
            if not setting_type:
                await websocket.send_json({
                    "type": "error",
                    "message": "setting_type is required",
                })
                continue

            token = payload.get("token") or None
            book_title = payload.get("book_title", "")
            genre = payload.get("genre", "")
            context = payload.get("context", "")
            prior_settings = payload.get("prior_settings") or []

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
                        await websocket.send_json({
                            "type": "chunk",
                            "content": data,
                        })
                    elif kind == "done":
                        await websocket.send_json({
                            "type": "done",
                            **data,
                        })
            except Exception as e:
                logger.exception(f"WS generate-setting failed: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    except Exception as e:
        logger.exception(f"WS unexpected error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
