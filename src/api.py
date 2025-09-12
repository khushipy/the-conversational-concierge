from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import os
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our agent and components
from .agent import WineConciergeAgent, AgentState
from .document_retriever import DocumentRetriever
from .weather import WeatherService
from .web_search import WebSearcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Wine Concierge API",
    description="API for the Wine Concierge conversational agent",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
agent = WineConciergeAgent()
document_retriever = DocumentRetriever()
weather_service = WeatherService()
web_searcher = WebSearcher()

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Pydantic models for request/response
class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    location: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    context: Optional[str] = None
    tool_used: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    message: str
    document_count: int

# API Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """
    Process a chat message and return the assistant's response.
    """
    try:
        # Convert messages to the format expected by the agent
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_request.messages[:-1]  # All messages except the last one
        ]
        
        # The last message is the current user message
        user_message = chat_request.messages[-1].content
        
        # Process the message with the agent
        result = await agent.process_message(user_message, conversation_history)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weather")
async def get_weather(location: str = "Napa,CA,US"):
    """
    Get current weather for a location.
    """
    try:
        weather_info = weather_service.get_weather_summary(location)
        return {"weather": weather_info}
    except Exception as e:
        logger.error(f"Error getting weather: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload")
async def upload_documents():
    """
    Upload and process documents to the knowledge base.
    Note: In a production app, you would handle file uploads here.
    """
    try:
        # In a real app, you would save and process uploaded files here
        # For now, we'll just reload the existing documents
        documents = document_retriever.load_documents()
        
        if documents:
            document_retriever.create_vector_store()
            document_retriever.save_vector_store()
            return {
                "message": f"Successfully processed {len(documents)} documents",
                "document_count": len(documents)
            }
        else:
            return {
                "message": "No documents found in the data directory",
                "document_count": 0
            }
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_web(query: str, num_results: int = 3):
    """
    Perform a web search.
    """
    try:
        results = web_searcher.search(query, num_results=num_results)
        return {"results": [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]}
    except Exception as e:
        logger.error(f"Error performing web search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "wine-concierge",
        "version": "1.0.0"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
