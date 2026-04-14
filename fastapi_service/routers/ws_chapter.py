"""WebSocket router for streaming chapter generation.

Protocol:
  Client -> Server (JSON):
    {"action": "start", "token": "<jwt>", "project_id": 123}
    {"action": "stop"}

  Server -> Client (JSON, multiple):
    {"type": "status",  "message": "正在生成第 N 章..."}
    {"type": "chunk",   "content": "文字片段"}
    {"type": "log",     "message": "...", "timestamp": "HH:MM:SS"}
    {"type": "done",    "chapter_id": 99, "chapter_number": 42, "word_count": 2048}
    {"type": "error",   "message": "..."}
"""
import asyncio
import json
import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from config import settings
from services.llm_client import llm_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Chapter Generation"])


async def _safe_send(websocket: WebSocket, data: dict) -> bool:
    try:
        if websocket.client_state != WebSocketState.CONNECTED:
            return False
        await websocket.send_json(data)
        return True
    except (WebSocketDisconnect, RuntimeError):
        return False


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def _save_chapter_to_django(
    token: str | None,
    project_id: int,
    content: str,
    word_count: int,
) -> dict | None:
    """POST to Django REST API to create/update the chapter. Returns chapter data or None."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    django_url = settings.django_api_url.rstrip("/")
    payload = {
        "project_id": project_id,
        "content": content,
        "word_count": word_count,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{django_url}/api/chapters/generate-from-ws/",
                json=payload,
                headers=headers,
            )
            if resp.status_code in (200, 201):
                return resp.json()
    except Exception as e:
        logger.error(f"[ws_chapter] Failed to save chapter: {e}")
    return None


@router.websocket("/ws/generate-chapter")
async def ws_generate_chapter(websocket: WebSocket):
    await websocket.accept()
    stop_event = asyncio.Event()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                await _safe_send(websocket, {"type": "error", "message": f"Invalid JSON: {e}"})
                continue

            action = payload.get("action")

            if action == "stop":
                stop_event.set()
                continue

            if action != "start":
                await _safe_send(websocket, {"type": "error", "message": f"Unknown action: {action}"})
                continue

            token = payload.get("token") or None
            project_id = payload.get("project_id")
            if not project_id:
                await _safe_send(websocket, {"type": "error", "message": "project_id is required"})
                continue

            # Reset stop flag for new generation
            stop_event.clear()

            # Fetch project info from Django to determine next chapter number
            next_chapter_number = 1
            chapter_title = "第1章"
            try:
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                django_url = settings.django_api_url.rstrip("/")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{django_url}/api/novels/{project_id}/generation-status/",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        total = data.get("total_chapters", 0)
                        next_chapter_number = total + 1
                        chapter_title = f"第{next_chapter_number}章"
            except Exception as e:
                logger.warning(f"[ws_chapter] Could not fetch generation status: {e}")

            if not await _safe_send(websocket, {
                "type": "status",
                "message": f"正在生成第 {next_chapter_number} 章...",
            }):
                return

            await _safe_send(websocket, {
                "type": "log",
                "message": f"开始生成第{next_chapter_number}章《{chapter_title}》",
                "timestamp": _timestamp(),
            })

            full_content = ""

            try:
                async for kind, data in llm_client.generate_chapter_stream(
                    project_id=project_id,
                    chapter_number=next_chapter_number,
                    chapter_title=chapter_title,
                    user_token=token,
                ):
                    if stop_event.is_set():
                        await _safe_send(websocket, {
                            "type": "log",
                            "message": "已手动停止生成",
                            "timestamp": _timestamp(),
                        })
                        break

                    if kind == "chunk":
                        full_content += data
                        if not await _safe_send(websocket, {"type": "chunk", "content": data}):
                            return

                    elif kind == "status":
                        await _safe_send(websocket, {
                            "type": "log",
                            "message": data,
                            "timestamp": _timestamp(),
                        })

                    elif kind == "done":
                        full_content = data.get("content", full_content)
                        word_count = data.get("word_count", 0)

                        await _safe_send(websocket, {
                            "type": "log",
                            "message": f"生成完毕，共 {word_count} 字，正在存档...",
                            "timestamp": _timestamp(),
                        })

                        # Save to Django
                        saved = await _save_chapter_to_django(token, project_id, full_content, word_count)
                        if saved:
                            await _safe_send(websocket, {
                                "type": "done",
                                "chapter_id": saved.get("id"),
                                "chapter_number": next_chapter_number,
                                "word_count": word_count,
                            })
                            await _safe_send(websocket, {
                                "type": "log",
                                "message": f"章节已保存（ID={saved.get('id')}）",
                                "timestamp": _timestamp(),
                            })
                        else:
                            await _safe_send(websocket, {
                                "type": "error",
                                "message": "生成完成，但保存失败，请联系管理员",
                            })

                    elif kind == "error":
                        await _safe_send(websocket, {"type": "error", "message": data})

            except Exception as e:
                logger.error(f"[ws_chapter] Generation error: {type(e).__name__}: {e}")
                await _safe_send(websocket, {"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[ws_chapter] Unexpected error: {type(e).__name__}: {e}")
        try:
            await _safe_send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
