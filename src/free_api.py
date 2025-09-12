"""FastAPI application for the Wine Concierge (Free Version)."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import os

# Import the free agent
from free_agent import WineConciergeAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Wine Concierge API (Free)")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
agent = WineConciergeAgent()

# Models
class WineRecommendationRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

class WineRecommendationResponse(BaseModel):
    recommendation: str
    sources: List[str]

# Routes
@app.get("/")
async def read_root():
    """Root endpoint."""
    return {"message": "Welcome to Wine Concierge API (Free Version)"}

@app.post("/api/recommend", response_model=WineRecommendationResponse)
async def get_recommendation(request: WineRecommendationRequest):
    """Get a wine recommendation."""
    try:
        result = agent.get_wine_recommendation(request.query)
        return WineRecommendationResponse(**result)
    except Exception as e:
        logger.error(f"Error in recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "free_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
