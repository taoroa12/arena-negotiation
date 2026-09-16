from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas

router = APIRouter(prefix="/admin/scenarios", tags=["admin"])


@router.post("", response_model=schemas.ScenarioOut)
def create_scenario(data: schemas.ScenarioCreate, db: Session = Depends(get_db)):
    scenario = models.Scenario(**data.model_dump())
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("", response_model=list[schemas.ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)):
    return db.query(models.Scenario).all()


@router.get("/{scenario_id}", response_model=schemas.ScenarioOut)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Сценарий не найден")
    return scenario


@router.put("/{scenario_id}", response_model=schemas.ScenarioOut)
def update_scenario(scenario_id: int, data: schemas.ScenarioCreate, db: Session = Depends(get_db)):
    scenario = db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Сценарий не найден")
    for key, value in data.model_dump().items():
        setattr(scenario, key, value)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}")
def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Сценарий не найден")
    db.delete(scenario)
    db.commit()
    return {"ok": True}