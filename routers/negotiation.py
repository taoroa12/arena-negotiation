from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import llm_client

router = APIRouter(prefix="/sessions", tags=["negotiation"])


@router.post("/start", response_model=dict)
def start_session(data: schemas.SessionStart, db: Session = Depends(get_db)):
    scenario = db.query(models.Scenario).filter(models.Scenario.id == data.scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Сценарий не найден")

    session = models.NegotiationSession(scenario_id=scenario.id, user_name=data.user_name)
    db.add(session)
    db.commit()
    db.refresh(session)

    opening = llm_client.get_opponent_reply(scenario, [])
    msg = models.Message(session_id=session.id, role="opponent", content=opening)
    db.add(msg)
    db.commit()

    return {"session_id": session.id, "opening_message": opening}


@router.post("/{session_id}/message")
def send_message(session_id: int, data: schemas.MessageIn, db: Session = Depends(get_db)):
    session = db.query(models.NegotiationSession).filter(models.NegotiationSession.id == session_id).first()
    if not session or session.status != "active":
        raise HTTPException(404, "Активная сессия не найдена")

    user_msg = models.Message(session_id=session.id, role="user", content=data.content)
    db.add(user_msg)
    db.commit()

    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(models.Message).filter(models.Message.session_id == session.id).order_by(models.Message.id)
    ]
    reply = llm_client.get_opponent_reply(session.scenario, history)

    opponent_msg = models.Message(session_id=session.id, role="opponent", content=reply)
    db.add(opponent_msg)
    db.commit()

    return {"reply": reply}


@router.get("/{session_id}", response_model=list[schemas.MessageOut])
def get_history(session_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.id)
        .all()
    )


@router.post("/{session_id}/finish", response_model=schemas.FeedbackOut)
def finish_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.NegotiationSession).filter(models.NegotiationSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Сессия не найдена")

    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(models.Message).filter(models.Message.session_id == session.id).order_by(models.Message.id)
    ]
    result = llm_client.get_feedback(session.scenario, history)

    feedback = models.Feedback(session_id=session.id, **result)
    db.add(feedback)

    session.status = "finished"
    session.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(feedback)

    return feedback