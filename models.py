from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    sphere = Column(String)
    topic = Column(String)
    difficulty = Column(String)
    tone = Column(String)
    opponent_role = Column(String)
    opponent_goals = Column(Text)
    context_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("NegotiationSession", back_populates="scenario")


class NegotiationSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    user_name = Column(String)
    status = Column(String, default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    scenario = relationship("Scenario", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    feedback = relationship("Feedback", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    role = Column(String)  # "user" или "opponent"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("NegotiationSession", back_populates="messages")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), unique=True)
    summary = Column(Text)
    strengths = Column(Text)
    weaknesses = Column(Text)
    score_goal = Column(Integer)
    score_argumentation = Column(Integer)
    score_empathy = Column(Integer)
    score_tactics = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("NegotiationSession", back_populates="feedback")