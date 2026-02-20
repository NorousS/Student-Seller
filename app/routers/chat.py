"""
Роутер чата.
WebSocket для real-time + REST для истории.
Чат доступен только после accepted запроса на контакт.
"""

import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token, get_current_user
from app.database import get_db, async_session_maker
from app.models import ContactRequest, ContactRequestStatus, Message, User

router = APIRouter(tags=["chat"])


# --- WebSocket connection manager ---


class ConnectionManager:
    """Менеджер WebSocket-соединений, группированных по contact_request_id."""

    def __init__(self):
        # {contact_request_id: {user_id: WebSocket}}
        self.active_connections: dict[int, dict[int, WebSocket]] = defaultdict(dict)

    async def connect(self, websocket: WebSocket, request_id: int, user_id: int):
        await websocket.accept()
        self.active_connections[request_id][user_id] = websocket

    def disconnect(self, request_id: int, user_id: int):
        self.active_connections[request_id].pop(user_id, None)
        if not self.active_connections[request_id]:
            del self.active_connections[request_id]

    async def send_to_other(self, request_id: int, sender_id: int, message: dict):
        """Отправить сообщение другому участнику чата."""
        connections = self.active_connections.get(request_id, {})
        for uid, ws in connections.items():
            if uid != sender_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


# --- WebSocket endpoint ---


@router.websocket("/ws/chat/{contact_request_id}")
async def websocket_chat(
    websocket: WebSocket,
    contact_request_id: int,
    token: str = Query(...),
):
    """
    WebSocket чат.
    Подключение: ws://host/ws/chat/{id}?token=JWT_ACCESS_TOKEN
    Сообщения: JSON {"text": "message text"}
    """
    # Auth
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Validate contact request
    async with async_session_maker() as db:
        cr = await db.execute(
            select(ContactRequest).where(ContactRequest.id == contact_request_id)
        )
        contact_request = cr.scalar_one_or_none()

        if not contact_request:
            await websocket.close(code=4004, reason="Contact request not found")
            return

        if contact_request.status != ContactRequestStatus.accepted:
            await websocket.close(code=4003, reason="Contact request not accepted")
            return

        # Check user is participant
        # Employer side: employer_id matches user_id
        # Student side: need to check student.user_id
        is_employer = contact_request.employer_id == user_id

        if not is_employer:
            from app.models import Student
            student_result = await db.execute(
                select(Student).where(Student.id == contact_request.student_id)
            )
            student = student_result.scalar_one_or_none()
            if not student or student.user_id != user_id:
                await websocket.close(code=4003, reason="Not a participant")
                return

    # Connect
    await manager.connect(websocket, contact_request_id, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                text = msg_data.get("text", "").strip()
            except json.JSONDecodeError:
                text = data.strip()

            if not text:
                continue

            # Save to DB
            async with async_session_maker() as db:
                message = Message(
                    contact_request_id=contact_request_id,
                    sender_id=user_id,
                    text=text,
                )
                db.add(message)
                await db.commit()
                await db.refresh(message)

                msg_response = {
                    "id": message.id,
                    "sender_id": user_id,
                    "text": text,
                    "created_at": message.created_at.isoformat(),
                    "is_read": False,
                }

            # Send to other participant
            await manager.send_to_other(contact_request_id, user_id, msg_response)
            # Echo back to sender
            await websocket.send_json(msg_response)

    except WebSocketDisconnect:
        manager.disconnect(contact_request_id, user_id)


# --- REST endpoints ---


@router.get("/api/v1/chat/{contact_request_id}/messages")
async def get_chat_messages(
    contact_request_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """История сообщений чата (с пагинацией)."""
    # Validate contact request exists and is accepted
    cr_result = await db.execute(
        select(ContactRequest).where(ContactRequest.id == contact_request_id)
    )
    cr = cr_result.scalar_one_or_none()
    if not cr:
        raise HTTPException(status_code=404, detail="Contact request not found")
    if cr.status != ContactRequestStatus.accepted:
        raise HTTPException(status_code=403, detail="Contact request not accepted")

    # Verify current user is a participant
    is_employer = cr.employer_id == current_user.id
    if not is_employer:
        from app.models import Student as StudentModel
        student_result = await db.execute(
            select(StudentModel).where(StudentModel.id == cr.student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student or student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not a participant")

    # Get messages
    stmt = (
        select(Message)
        .where(Message.contact_request_id == contact_request_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
            "is_read": m.is_read,
        }
        for m in messages
    ]


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/api/v1/chat/{contact_request_id}/messages")
async def send_message_rest(
    contact_request_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отправить сообщение (REST fallback)."""
    cr_result = await db.execute(
        select(ContactRequest).where(ContactRequest.id == contact_request_id)
    )
    cr = cr_result.scalar_one_or_none()
    if not cr:
        raise HTTPException(status_code=404, detail="Contact request not found")
    if cr.status != ContactRequestStatus.accepted:
        raise HTTPException(status_code=403, detail="Contact request not accepted")

    # Verify sender is a participant
    is_employer = cr.employer_id == current_user.id
    if not is_employer:
        from app.models import Student as StudentModel
        student_result = await db.execute(
            select(StudentModel).where(StudentModel.id == cr.student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student or student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not a participant")

    message = Message(
        contact_request_id=contact_request_id,
        sender_id=current_user.id,
        text=body.text,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "text": message.text,
        "created_at": message.created_at.isoformat(),
        "is_read": message.is_read,
    }
