from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from api.auth import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Keep track of last sync and status
job_state = {
    "last_sync": None,
    "status": "idle"
}

def execute_sync():
    global job_state
    try:
        from api.jobs import run_scraper_job
        job_state["status"] = "running"
        run_scraper_job()
        job_state["last_sync"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    finally:
        job_state["status"] = "idle"

@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, current_user = Depends(get_current_user)):
    global job_state
    if job_state["status"] == "running":
        raise HTTPException(status_code=400, detail="Sync already in progress.")
    background_tasks.add_task(execute_sync)
    return {"message": "Sync started in the background."}

@router.get("/status")
async def get_sync_status(current_user = Depends(get_current_user)):
    return job_state
