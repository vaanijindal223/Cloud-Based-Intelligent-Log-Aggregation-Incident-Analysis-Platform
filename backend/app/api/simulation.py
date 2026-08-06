from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.simulation.failures import FAILURES
from app.simulation.manager import NoRunningSimulation, SimulationAlreadyRunning, manager
from app.simulation.models import Speed
from app.simulation.workflows import WORKFLOWS

router = APIRouter(prefix="/simulation")


class StartSimulationRequest(BaseModel):
    workflow: str = "ecommerce"
    failure: str = "none"
    speed: Speed = Speed.NORMAL


@router.get("/workflows")
def list_workflows():
    return [{"name": w.name, "description": w.description} for w in WORKFLOWS.values()]


@router.get("/failures")
def list_failures():
    return [{"name": f.name, "description": f.description} for f in FAILURES.values()]


@router.post("/start")
async def start_simulation(request: StartSimulationRequest):
    if request.workflow not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Unknown workflow '{request.workflow}'")
    if request.failure not in FAILURES:
        raise HTTPException(status_code=404, detail=f"Unknown failure '{request.failure}'")
    try:
        return manager.start(request.workflow, request.failure, request.speed)
    except SimulationAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/stop")
def stop_simulation():
    try:
        return manager.stop()
    except NoRunningSimulation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/status")
def simulation_status():
    return manager.status()
