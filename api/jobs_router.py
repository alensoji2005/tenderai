from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from api.auth import get_current_user
from api.jobs import job_state, run_scraper_job

router = APIRouter()


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, current_user = Depends(get_current_user)):
    if job_state["status"] == "running":
        raise HTTPException(status_code=400, detail="Sync already in progress.")
    job_state["status"] = "running"  # claim immediately so a second click is rejected
    background_tasks.add_task(run_scraper_job)
    return {"message": "Sync started in the background."}


@router.get("/status")
async def get_sync_status(current_user = Depends(get_current_user)):
    return job_state
