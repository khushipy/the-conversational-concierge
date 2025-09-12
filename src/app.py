"""Wine Concierge - Local Version

A smart wine recommendation system using local LLM and web search.
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
from pathlib import Path

# Import configuration
from config.local_config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the current file's directory
BASE_DIR = Path(__file__).resolve().parent

# Initialize FastAPI
app = FastAPI(title="Wine Concierge", version="1.0.0")

# Configure templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class WineRecommendationRequest(BaseModel):
    """Request model for wine recommendations."""
    query: str
    max_results: Optional[int] = settings.SEARCH_MAX_RESULTS

class WineRecommendationResponse(BaseModel):
    """Response model for wine recommendations."""
    recommendation: str
    sources: List[Dict[str, str]]

# Initialize components
def get_llm():
    """Initialize and return a lightweight text generation pipeline."""
    try:
        # Using a small, fast model for local inference
        from transformers import pipeline
        return pipeline(
            "text-generation",
            model="facebook/opt-125m",  # Very small model
            device_map="auto"
        )
    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        raise

def get_search_client():
    """Initialize and return the search client."""
    from duckduckgo_search import DDGS
    return DDGS()

# Initialize components
llm = get_llm()
search_client = get_search_client()

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Wine Concierge"}
    )

# Explicit static file routes as fallback
@app.get("/static/{file_path:path}")
async def static_file(file_path: str):
    static_file_path = BASE_DIR / "static" / file_path
    if static_file_path.exists():
        return FileResponse(static_file_path)
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/recommend", response_model=WineRecommendationResponse)
async def recommend_wine(request: WineRecommendationRequest):
    """Get a wine recommendation based on the query."""
    try:
        # Search for relevant information
        search_results = search_client.text(
            f"wine recommendation {request.query}",
            max_results=request.max_results
        )
        
        # Format search results
        formatted_results = [
            {"title": r["title"], "url": r["href"], "snippet": r["body"][:200] + "..."}
            for r in search_results
        ]
        
        # Build the prompt
        prompt = f"""You are a knowledgeable wine concierge. Provide a detailed wine recommendation based on the following query and search results.
        
        Query: {request.query}
        
        Search Results:
        {search_context}
        
        Please provide:
        1. Wine recommendation with details (grape, region, style)
        2. Tasting notes
        3. Food pairing suggestions
        4. Price range
        5. Any additional tips or information
        """.format(
            search_context="\n\n".join([f"- {r['title']}: {r['snippet']}" for r in formatted_results])
        )
        
        # Generate the response
        response = llm.generate(
            prompt=prompt,
            temp=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        
        return {
            "recommendation": response.strip(),
            "sources": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error in recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": app.version,
        "environment": settings.ENVIRONMENT,
        "llm_model": settings.LLM_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    
    # Create models directory if it doesn't exist
    os.makedirs(settings.LLM_MODEL_PATH, exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
