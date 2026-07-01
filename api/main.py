# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI and Prisma
app = FastAPI(
    title="TenderAI Oman API",
    description="Backend for AI-powered tender intelligence",
    version="1.0.0"
)
db = Prisma()

# Configure CORS (Allows your future React frontend to talk to this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, we will restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to the Database when the server starts
@app.on_event("startup")
async def startup():
    logger.info("Connecting to PostgreSQL database via Prisma...")
    await db.connect()
    logger.info("Database connection established.")
    
    # Start background scraper jobs
    from api.jobs import start_jobs
    start_jobs()

# Disconnect when the server shuts down
@app.on_event("shutdown")
async def shutdown():
    # Stop background scraper jobs
    from api.jobs import stop_jobs
    stop_jobs()
    
    logger.info("Disconnecting from database...")
    await db.disconnect()

# Health Check Endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TenderAI API",
        "version": "1.0.0"
    }

# api/main.py (Add to the bottom)
from api.tenders import router as tenders_router
from api.competitors import router as competitors_router
from api.ml import router as ml_router
from api.auth import router as auth_router
from api.stats import router as stats_router

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(tenders_router, prefix="/api/tenders", tags=["Tenders"])
app.include_router(competitors_router, prefix="/api/competitors", tags=["Competitors"])
app.include_router(ml_router, prefix="/api/ml", tags=["Intelligence"])
app.include_router(stats_router, prefix="/api/stats", tags=["Stats"])