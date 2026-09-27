from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    title: str
    sphere: str
    topic: str
    difficulty: str
    tone: str
    opponent_role: str
    opponent_goals: str
    context_description: str


class ScenarioOut(ScenarioCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionStart(BaseModel):
    scenario_id: int
    user_name: str


class MessageIn(BaseModel):
    content: str


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    scenario_id: int
    user_name: str
    status: str
    started_at: datetime

    class Config:
        from_attributes = True


class FeedbackOut(BaseModel):
    summary: str
    strengths: str
    weaknesses: str
    deal_status: str
    deal_terms: str
    score_goal: int
    score_argumentation: int
    score_empathy: int
    score_tactics: int

    class Config:
        from_attributes = True