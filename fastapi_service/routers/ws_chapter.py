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
import time
import uuid
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


def _with_session(data: dict, session_id: str | None) -> dict:
    if not session_id:
        return data
    return {
        **data,
        "session_id": session_id,
    }


async def _save_chapter_to_django(
    token: str | None,
    project_id: int,
    chapter_number: int,
    chapter_title: str,
    content: str,
    word_count: int,
    generation_meta: dict,
    context_snapshot: dict,
) -> dict | None:
    """POST to Django REST API to create/update the chapter. Returns chapter data or None."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    django_url = settings.django_api_url.rstrip("/")
    payload = {
        "project_id": project_id,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "content": content,
        "word_count": word_count,
        "generation_meta": generation_meta,
        "context_snapshot": context_snapshot,
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


async def _fetch_generation_context(
    token: str | None,
    project_id: int,
    chapter_number: int,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    django_url = settings.django_api_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{django_url}/api/workbench/{project_id}/generation-context/",
                params={'chapter_number': chapter_number},
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"[ws_chapter] Could not fetch generation context: {exc}")
    return {}


async def _fetch_generation_status(token: str | None, project_id: int) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    django_url = settings.django_api_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{django_url}/api/novels/{project_id}/generation-status/",
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"[ws_chapter] Could not fetch generation status: {exc}")
    return {}


def _safe_int(value, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _word_count(content: str) -> int:
    return len([char for char in content if not char.isspace()])


def _mode_label(mode: str) -> str:
    return {
        "generate": "生成",
        "continue": "续写",
        "regenerate": "重写",
    }.get(mode, "生成")


async def _iter_text_chunks(content: str, chunk_size: int = 12):
    for index in range(0, len(content), chunk_size):
        yield content[index:index + chunk_size]
        await asyncio.sleep(0.03)


async def _resolve_target(payload: dict, token: str | None) -> dict:
    project_id = _safe_int(payload.get("project_id"))
    if not project_id:
        raise ValueError("project_id is required")

    mode = (payload.get("mode") or "generate").strip().lower()
    if mode not in {"generate", "continue", "regenerate"}:
        raise ValueError(f"Unsupported mode: {mode}")

    run_mode = (payload.get("run_mode") or "").strip().lower() or None

    status_payload = await _fetch_generation_status(token, project_id)
    total_chapters = _safe_int(status_payload.get("total_chapters"), 0) or 0
    current_chapter = _safe_int(status_payload.get("current_chapter"), total_chapters) or total_chapters
    project_target_chapters = _safe_int(status_payload.get("target_chapters"), 0) or 0

    chapter_number = _safe_int(payload.get("chapter_number"))
    if mode == "generate":
        chapter_number = chapter_number or total_chapters + 1
    else:
        chapter_number = chapter_number or current_chapter
        if not chapter_number:
            raise ValueError("当前项目还没有可续写或重写的章节")

    requested_target_chapter = _safe_int(payload.get("target_chapter"))
    if run_mode is None:
        run_mode = "continuous" if (mode == "generate" and requested_target_chapter) else "single"
    if run_mode not in {"single", "continuous"}:
        raise ValueError(f"Unsupported run_mode: {run_mode}")
    if run_mode == "continuous" and mode != "generate":
        raise ValueError("连续迭代只支持生成新章节")

    target_chapter = requested_target_chapter or chapter_number
    if run_mode == "continuous" and requested_target_chapter is None:
        target_chapter = project_target_chapters or chapter_number
    if target_chapter < chapter_number:
        raise ValueError(f"目标章节不能小于第 {chapter_number} 章")

    chapter_title = (payload.get("chapter_title") or "").strip() or f"第{chapter_number}章"
    current_content = payload.get("current_content") or ""
    continue_length = _safe_int(payload.get("continue_length"), 1200) or 1200

    return {
        "project_id": project_id,
        "mode": mode,
        "run_mode": run_mode,
        "chapter_number": chapter_number,
        "target_chapter": target_chapter,
        "project_target_chapters": project_target_chapters,
        "chapter_title": chapter_title,
        "current_content": current_content,
        "continue_length": continue_length,
    }


async def _stream_generation(target: dict, context_snapshot: dict, token: str | None):
    mode = target["mode"]

    if mode == "continue":
        current_content = target.get("current_content") or ""
        if not current_content.strip():
            raise ValueError("continue 模式需要 current_content")

        continued_content, _continued_words = await llm_client.continue_content(
            current_content=current_content,
            continue_length=target["continue_length"],
            user_token=token,
        )

        joiner = "\n\n" if current_content and not current_content.endswith("\n") else ""
        full_content = f"{current_content}{joiner}{continued_content}".strip()
        async for chunk in _iter_text_chunks(continued_content):
            yield ("chunk", chunk)
        yield (
            "done",
            {
                "content": full_content,
                "word_count": _word_count(full_content),
            },
        )
        return

    async for item in llm_client.generate_chapter_stream(
        project_id=target["project_id"],
        chapter_number=target["chapter_number"],
        chapter_title=target["chapter_title"],
        context_payload=context_snapshot,
        user_token=token,
    ):
        yield item


async def _watch_control_messages(
    websocket: WebSocket,
    stop_event: asyncio.Event,
    session_id: str,
):
    while websocket.client_state == WebSocketState.CONNECTED and not stop_event.is_set():
        raw = await websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            await _safe_send(
                websocket,
                _with_session(
                    {"type": "error", "message": "控制消息不是合法 JSON"},
                    session_id,
                ),
            )
            continue

        action = payload.get("action")
        payload_session_id = payload.get("session_id")
        if payload_session_id and payload_session_id != session_id:
            continue

        if action == "stop":
            stop_event.set()
            await _safe_send(
                websocket,
                _with_session(
                    {
                        "type": "log",
                        "message": "已接收停止指令，本章收尾后结束迭代",
                        "timestamp": _timestamp(),
                    },
                    session_id,
                ),
            )
        elif action == "start":
            await _safe_send(
                websocket,
                _with_session(
                    {
                        "type": "error",
                        "message": "已有生成任务正在运行，请先停止当前任务",
                    },
                    session_id,
                ),
            )


async def _run_generation_session(
    websocket: WebSocket,
    token: str | None,
    session_id: str,
    target: dict,
    stop_event: asyncio.Event,
) -> None:
    project_id = target["project_id"]
    mode = target["mode"]
    run_mode = target["run_mode"]
    action_label = _mode_label(mode)
    session_started_at = datetime.now()
    start_chapter = target["chapter_number"]
    target_chapter = target["target_chapter"]

    await _safe_send(
        websocket,
        _with_session(
            {
                "type": "log",
                "message": (
                    f"已启动连续迭代，将从第{start_chapter}章写到第{target_chapter}章"
                    if run_mode == "continuous"
                    else f"已启动单章{action_label}任务"
                ),
                "timestamp": _timestamp(),
                "chapter_number": start_chapter,
                "mode": mode,
                "run_mode": run_mode,
                "target_chapter": target_chapter,
            },
            session_id,
        ),
    )

    current_chapter = start_chapter
    completed_chapters = 0
    last_saved_chapter: dict | None = None
    stop_reason = "completed"

    while current_chapter <= target_chapter:
        if stop_event.is_set():
            stop_reason = "stopped"
            break

        current_target = {
            **target,
            "chapter_number": current_chapter,
            "chapter_title": target["chapter_title"] if run_mode == "single" else f"第{current_chapter}章",
        }
        chapter_started_at = datetime.now()
        started_perf = time.perf_counter()
        context_snapshot = await _fetch_generation_context(
            token,
            project_id,
            current_chapter,
        ) or {
            "project_id": project_id,
            "chapter_number": current_chapter,
            "chapter_title": current_target["chapter_title"],
            "transport": "websocket",
            "session_id": session_id,
        }
        context_snapshot["transport"] = "websocket"
        context_snapshot["session_id"] = session_id
        context_snapshot["mode"] = mode
        context_snapshot["run_mode"] = run_mode
        context_snapshot["target_chapter"] = target_chapter
        context_snapshot["chapter_title"] = current_target["chapter_title"]

        if not await _safe_send(
            websocket,
            _with_session(
                {
                    "type": "status",
                    "message": f"正在{action_label}第 {current_chapter} 章...",
                    "chapter_number": current_chapter,
                    "mode": mode,
                    "run_mode": run_mode,
                    "target_chapter": target_chapter,
                    "status_kind": "chapter_start",
                },
                session_id,
            ),
        ):
            return

        await _safe_send(
            websocket,
            _with_session(
                {
                    "type": "log",
                    "message": f"开始{action_label}第{current_chapter}章《{current_target['chapter_title']}》",
                    "timestamp": _timestamp(),
                    "chapter_number": current_chapter,
                    "mode": mode,
                    "run_mode": run_mode,
                    "target_chapter": target_chapter,
                },
                session_id,
            ),
        )

        full_content = ""
        chapter_saved = False

        try:
            async for kind, data in _stream_generation(current_target, context_snapshot, token):
                if stop_event.is_set():
                    stop_reason = "stopped"
                    break

                if kind == "chunk":
                    full_content += data
                    if not await _safe_send(
                        websocket,
                        _with_session(
                            {
                                "type": "chunk",
                                "content": data,
                                "chapter_number": current_chapter,
                                "mode": mode,
                                "run_mode": run_mode,
                                "target_chapter": target_chapter,
                            },
                            session_id,
                        ),
                    ):
                        return

                elif kind == "status":
                    await _safe_send(
                        websocket,
                        _with_session(
                            {
                                "type": "log",
                                "message": data,
                                "timestamp": _timestamp(),
                                "chapter_number": current_chapter,
                                "mode": mode,
                                "run_mode": run_mode,
                                "target_chapter": target_chapter,
                            },
                            session_id,
                        ),
                    )

                elif kind == "done":
                    full_content = data.get("content", full_content)
                    word_count = data.get("word_count", 0)
                    finished_at = datetime.now()
                    generation_meta = {
                        "task_type": "chapter" if mode == "generate" else mode,
                        "transport": "websocket",
                        "session_id": session_id,
                        "session_started_at": session_started_at.isoformat(),
                        "started_at": chapter_started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                        "latency_ms": int((time.perf_counter() - started_perf) * 1000),
                        "word_count": word_count,
                        "mode": mode,
                        "run_mode": run_mode,
                        "target_chapter": target_chapter,
                    }

                    await _safe_send(
                        websocket,
                        _with_session(
                            {
                                "type": "log",
                                "message": f"{action_label}完毕，共 {word_count} 字，正在存档...",
                                "timestamp": _timestamp(),
                                "chapter_number": current_chapter,
                                "mode": mode,
                                "run_mode": run_mode,
                                "target_chapter": target_chapter,
                            },
                            session_id,
                        ),
                    )

                    saved = await _save_chapter_to_django(
                        token,
                        project_id,
                        current_chapter,
                        current_target["chapter_title"],
                        full_content,
                        word_count,
                        generation_meta,
                        context_snapshot,
                    )
                    if not saved:
                        await _safe_send(
                            websocket,
                            _with_session(
                                {
                                    "type": "error",
                                    "message": "生成完成，但保存失败，请联系管理员",
                                },
                                session_id,
                            ),
                        )
                        return

                    completed_chapters += 1
                    chapter_saved = True
                    last_saved_chapter = saved
                    save_event_id = uuid.uuid4().hex

                    await _safe_send(
                        websocket,
                        _with_session(
                            {
                                "type": "chapter_saved",
                                "chapter_id": saved.get("id"),
                                "chapter_number": current_chapter,
                                "word_count": word_count,
                                "mode": mode,
                                "run_mode": run_mode,
                                "target_chapter": target_chapter,
                                "completed_chapters": completed_chapters,
                                "save_event_id": save_event_id,
                            },
                            session_id,
                        ),
                    )
                    await _safe_send(
                        websocket,
                        _with_session(
                            {
                                "type": "log",
                                "message": f"第{current_chapter}章已保存（ID={saved.get('id')}）",
                                "timestamp": _timestamp(),
                                "chapter_number": current_chapter,
                                "mode": mode,
                                "run_mode": run_mode,
                                "target_chapter": target_chapter,
                            },
                            session_id,
                        ),
                    )
                    break

                elif kind == "error":
                    await _safe_send(
                        websocket,
                        _with_session({"type": "error", "message": data}, session_id),
                    )
                    return
        except Exception as exc:
            logger.error(f"[ws_chapter] Generation error: {type(exc).__name__}: {exc}")
            await _safe_send(
                websocket,
                _with_session({"type": "error", "message": str(exc)}, session_id),
            )
            return

        if stop_event.is_set():
            stop_reason = "stopped"
            break
        if not chapter_saved:
            stop_reason = "stopped"
            break
        if run_mode != "continuous":
            stop_reason = "completed"
            break
        if current_chapter >= target_chapter:
            stop_reason = "target_reached"
            break

        current_chapter += 1

    final_chapter_number = last_saved_chapter.get("chapter_number") if last_saved_chapter else None
    final_chapter_id = last_saved_chapter.get("id") if last_saved_chapter else None
    final_word_count = last_saved_chapter.get("word_count") if last_saved_chapter else None
    if stop_reason == "target_reached":
        final_message = f"已达到目标章节第{target_chapter}章，自动停止迭代"
    elif stop_reason == "stopped":
        final_message = "已停止连续迭代"
    else:
        final_message = f"{action_label}任务已完成"

    await _safe_send(
        websocket,
        _with_session(
            {
                "type": "done",
                "chapter_id": final_chapter_id,
                "chapter_number": final_chapter_number,
                "word_count": final_word_count,
                "mode": mode,
                "run_mode": run_mode,
                "target_chapter": target_chapter,
                "completed_chapters": completed_chapters,
                "stop_reason": stop_reason,
                "message": final_message,
            },
            session_id,
        ),
    )


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
                await _safe_send(
                    websocket,
                    _with_session(
                        {
                            "type": "log",
                            "message": "已接收停止指令",
                            "timestamp": _timestamp(),
                        },
                        payload.get("session_id"),
                    ),
                )
                continue

            if action != "start":
                await _safe_send(websocket, {"type": "error", "message": f"Unknown action: {action}"})
                continue

            token = payload.get("token") or None
            session_id = payload.get("session_id") or uuid.uuid4().hex
            try:
                target = await _resolve_target(payload, token)
            except ValueError as exc:
                await _safe_send(
                    websocket,
                    _with_session({"type": "error", "message": str(exc)}, session_id),
                )
                continue

            stop_event.clear()
            control_task = asyncio.create_task(
                _watch_control_messages(websocket, stop_event, session_id)
            )
            try:
                await _run_generation_session(
                    websocket=websocket,
                    token=token,
                    session_id=session_id,
                    target=target,
                    stop_event=stop_event,
                )
            except WebSocketDisconnect:
                stop_event.set()
                return
            finally:
                stop_event.set()
                control_task.cancel()
                await asyncio.gather(control_task, return_exceptions=True)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[ws_chapter] Unexpected error: {type(e).__name__}: {e}")
        try:
            await _safe_send(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
