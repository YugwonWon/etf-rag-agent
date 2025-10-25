"""
FastAPI REST Server for ETF RAG Agent
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import json
from loguru import logger

from app.config import get_settings
from app.retriever.query_handler import RAGQueryHandler
from app.vector_store.weaviate_handler import WeaviateHandler
from app.crawler.collector import ETFDataCollector
from app.scheduler import get_scheduler


# Initialize FastAPI app
app = FastAPI(
    title="ETF RAG Agent API",
    description="RAG-based ETF information query system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
settings = get_settings()
vector_handler = None
rag_handler = None
collector = None
scheduler = None


# Pydantic models
class QuestionRequest(BaseModel):
    question: str = Field(..., description="User question about ETFs")
    model_type: Optional[str] = Field(None, description="LLM model type: 'openai' or 'local'")
    etf_type: Optional[str] = Field(None, description="Filter by ETF type: 'domestic' or 'foreign'")
    top_k: Optional[int] = Field(5, description="Number of documents to retrieve")
    temperature: Optional[float] = Field(0.7, description="LLM temperature (0-2)")


class AnswerResponse(BaseModel):
    answer: str
    sources: List[Dict]
    num_sources: int
    model_type: str
    question: str


class ETFSummaryRequest(BaseModel):
    etf_code: str = Field(..., description="ETF code or ticker")


class CollectionRequest(BaseModel):
    domestic: bool = Field(True, description="Collect domestic ETFs")
    foreign: bool = Field(True, description="Collect foreign ETFs")
    dart: bool = Field(True, description="Collect DART disclosures")
    domestic_max: Optional[int] = Field(None, description="Max domestic ETFs to collect")


class CollectionResponse(BaseModel):
    success: bool
    message: str
    domestic_count: int
    foreign_count: int
    dart_count: int
    total_count: int


class HealthResponse(BaseModel):
    healthy: bool
    status: str
    version: str
    total_documents: int
    timestamp: str


# Utility functions
def get_vector_handler():
    """Get or create vector handler"""
    global vector_handler
    if vector_handler is None:
        vector_handler = WeaviateHandler()
    return vector_handler


def get_rag_handler(model_type: str = None):
    """Get or create RAG handler"""
    global rag_handler
    if rag_handler is None or (model_type and rag_handler.model_type != model_type):
        rag_handler = RAGQueryHandler(
            vector_handler=get_vector_handler(),
            model_type=model_type
        )
    return rag_handler


def get_collector():
    """Get or create collector"""
    global collector
    if collector is None:
        collector = ETFDataCollector(
            vector_handler=get_vector_handler(),
            model_type=settings.llm_provider
        )
    return collector


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting ETF RAG Agent API server...")
    
    # Initialize components
    get_vector_handler()
    get_rag_handler()
    
    # Start scheduler if enabled
    if settings.enable_scheduler:
        global scheduler
        scheduler = get_scheduler()
        # run_immediately는 RUN_INITIAL_COLLECTION 환경 변수로 제어
        # Render 배포 시: False (포트 스캔 타임아웃 방지)
        # 로컬 개발 시: True (최신 데이터 보장)
        scheduler.start(run_immediately=settings.run_initial_collection)
        logger.info(f"Scheduler started (initial collection: {settings.run_initial_collection})")
    
    logger.info("API server started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API server...")
    
    if scheduler:
        scheduler.stop()
    
    if vector_handler:
        vector_handler.close()
    
    logger.info("API server stopped")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "name": "ETF RAG Agent API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "query": "/api/query",
            "summary": "/api/etf/{etf_code}",
            "collection": "/api/collection/trigger",
            "health": "/api/health",
            "docs": "/docs"
        }
    }


@app.post("/api/query", response_model=AnswerResponse, tags=["Query"])
async def query_etf(request: QuestionRequest):
    """
    Ask a question about ETFs
    
    Returns answer with sources and references
    """
    try:
        logger.info(f"Query: {request.question}")
        
        # Get RAG handler
        handler = get_rag_handler(request.model_type)
        
        # Prepare filters
        filters = {}
        if request.etf_type:
            filters["etf_type"] = request.etf_type
        
        # Query
        response = handler.query(
            question=request.question,
            top_k=request.top_k,
            filters=filters if filters else None,
            temperature=request.temperature
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error in query endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/etf/{etf_code}", tags=["ETF Info"])
async def get_etf_summary(etf_code: str):
    """
    Get comprehensive summary of an ETF
    """
    try:
        handler = get_rag_handler()
        
        summary = handler.get_etf_summary(etf_code)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"ETF not found: {etf_code}"
            )
        
        return summary
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ETF summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/collection/trigger", response_model=CollectionResponse, tags=["Data Collection"])
async def trigger_collection(
    request: CollectionRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger manual data collection
    
    Runs in background and returns immediately
    """
    try:
        def run_collection():
            """Background task for collection"""
            logger.info("Background collection started")
            
            coll = get_collector()
            
            results = {
                "domestic": [],
                "foreign": [],
                "dart": []
            }
            
            if request.domestic:
                results["domestic"] = coll.collect_domestic_etfs(
                    max_items=request.domestic_max,
                    insert_to_db=True
                )
            
            if request.foreign:
                results["foreign"] = coll.collect_foreign_etfs(
                    insert_to_db=True
                )
            
            if request.dart:
                results["dart"] = coll.collect_dart_disclosures(
                    insert_to_db=True
                )
            
            total = len(results["domestic"]) + len(results["foreign"]) + len(results["dart"])
            
            logger.info(f"Background collection completed: {total} items")
        
        # Add to background tasks
        background_tasks.add_task(run_collection)
        
        return CollectionResponse(
            success=True,
            message="Collection started in background",
            domestic_count=0,
            foreign_count=0,
            dart_count=0,
            total_count=0
        )
    
    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collection/status", tags=["Data Collection"])
async def get_collection_status():
    """
    Get current collection status and metadata
    """
    try:
        # Read metadata file
        metadata_path = settings.metadata_file
        
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {
                "last_updated": None,
                "etf_count": {"domestic": 0, "foreign": 0}
            }
        
        # Get document count from vector DB
        handler = get_vector_handler()
        total_docs = handler.get_document_count()
        
        metadata["total_documents"] = total_docs
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error getting collection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check endpoint
    """
    try:
        handler = get_vector_handler()
        doc_count = handler.get_document_count()
        
        return HealthResponse(
            healthy=True,
            status="OK",
            version="0.1.0",
            total_documents=doc_count,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            healthy=False,
            status=f"ERROR: {str(e)}",
            version="0.1.0",
            total_documents=0,
            timestamp=datetime.now().isoformat()
        )


@app.get("/api/scheduler/jobs", tags=["Scheduler"])
async def get_scheduler_jobs():
    """
    Get list of scheduled jobs
    """
    if not scheduler:
        raise HTTPException(
            status_code=404,
            detail="Scheduler is not enabled"
        )
    
    try:
        jobs = scheduler.get_jobs()
        return {"jobs": jobs}
    
    except Exception as e:
        logger.error(f"Error getting scheduler jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run server
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
