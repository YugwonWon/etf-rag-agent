"""
FastAPI REST Server for ETF RAG Agent
"""
print("🔵 main.py: Starting imports...")

from fastapi import FastAPI, HTTPException, BackgroundTasks
print("🔵 FastAPI imported")

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import json
print("🔵 Standard libraries imported")

from loguru import logger
print("🔵 loguru imported")

from app.config import get_settings
print("🔵 config imported")

from app.retriever.query_handler import RAGQueryHandler
print("🔵 query_handler imported")

from app.vector_store.weaviate_handler import WeaviateHandler
print("🔵 weaviate_handler imported")

from app.crawler.collector import ETFDataCollector
print("🔵 collector imported")

from app.scheduler import get_scheduler
print("🔵 scheduler imported")

print("✅ All imports successful")


print("🔵 Creating FastAPI app...")
# Initialize FastAPI app
app = FastAPI(
    title="ETF RAG Agent API",
    description="RAG-based ETF information query system",
    version="0.1.0"
)
print("✅ FastAPI app created")

print("🔵 Adding CORS middleware...")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("✅ CORS middleware added")

print("🔵 Initializing settings...")
# Global instances
settings = get_settings()
print(f"✅ Settings loaded: {settings.environment}")

vector_handler = None
rag_handler = None
collector = None
scheduler = None
print("✅ Global variables initialized")

print("=" * 60)
print("🎉 main.py module initialization complete")
print("=" * 60)


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
        try:
            vector_handler = WeaviateHandler()
            logger.info("Vector handler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector handler: {e}")
            raise
    return vector_handler


def get_rag_handler(model_type: str = None):
    """Get or create RAG handler"""
    global rag_handler
    if rag_handler is None or (model_type and rag_handler.model_type != model_type):
        try:
            rag_handler = RAGQueryHandler(
                vector_handler=get_vector_handler(),
                model_type=model_type
            )
            logger.info(f"RAG handler initialized with model type: {model_type or 'default'}")
        except Exception as e:
            logger.error(f"Failed to initialize RAG handler: {e}")
            raise
    return rag_handler


def get_collector():
    """Get or create collector"""
    global collector
    if collector is None:
        try:
            collector = ETFDataCollector(
                vector_handler=get_vector_handler(),
                model_type=settings.llm_provider
            )
            logger.info("Collector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize collector: {e}")
            raise
    return collector


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup - FAIL SAFE"""
    global vector_handler, rag_handler, scheduler
    
    print("=" * 60)
    print("🚀 ETF RAG Agent API - Starting up...")
    print(f"Environment: {settings.environment}")
    print(f"Scheduler: {settings.enable_scheduler}")
    print(f"Initial collection: {settings.run_initial_collection}")
    print("=" * 60)
    
    # Critical: Log to stdout for Render visibility
    logger.info("=" * 60)
    logger.info("Starting ETF RAG Agent API server...")
    logger.info(f"Environment: {settings.environment}")
    
    # DO NOT block startup with initialization
    # Let the server start first, initialize in background
    logger.info("Server starting... (components will initialize in background)")
    logger.info("=" * 60)
    
    logger.info("API server started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API server...")
    
    try:
        if scheduler:
            scheduler.stop()
            logger.info("✓ Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
    
    try:
        if vector_handler:
            vector_handler.close()
            logger.info("✓ Vector handler closed")
    except Exception as e:
        logger.error(f"Error closing vector handler: {e}")
    
    logger.info("API server stopped")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint - Simple health check"""
    return {
        "service": "ETF RAG Agent API",
        "version": "0.1.0",
        "status": "running",
        "message": "Server is alive",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/query", response_model=AnswerResponse, tags=["Query"])
async def query_etf(request: QuestionRequest):
    """
    Ask a question about ETFs
    
    Returns answer with sources and references
    Note: Render free plan has 30s timeout limit
    """
    try:
        logger.info(f"Query: {request.question}")
        
        # Get RAG handler
        handler = get_rag_handler(request.model_type)
        
        # Prepare filters
        filters = {}
        if request.etf_type:
            filters["etf_type"] = request.etf_type
        
        # Query with timeout handling
        import asyncio
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    handler.query,
                    question=request.question,
                    top_k=request.top_k,
                    filters=filters if filters else None,
                    temperature=request.temperature
                ),
                timeout=28.0  # Render 타임아웃(30s)보다 짧게 설정
            )
            return response
        except asyncio.TimeoutError:
            logger.error("Query timeout exceeded (28s)")
            raise HTTPException(
                status_code=504,
                detail="요청 처리 시간이 초과되었습니다. 더 짧은 질문을 시도해보세요."
            )
    
    except HTTPException:
        raise
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
            """Background task for collection - simplified without signal"""
            try:
                logger.info("Background collection started")
                
                coll = get_collector()
                
                results = {
                    "domestic": [],
                    "foreign": [],
                    "dart": []
                }
                
                if request.domestic:
                    try:
                        logger.info(f"Starting domestic ETF collection (max: {request.domestic_max})...")
                        results["domestic"] = coll.collect_domestic_etfs(
                            max_items=request.domestic_max,
                            insert_to_db=True
                        )
                        logger.info(f"Domestic collection completed: {len(results['domestic'])} items")
                    except Exception as e:
                        logger.error(f"Domestic collection failed: {e}")
                
                if request.foreign:
                    try:
                        logger.info("Starting foreign ETF collection...")
                        results["foreign"] = coll.collect_foreign_etfs(
                            insert_to_db=True
                        )
                        logger.info(f"Foreign collection completed: {len(results['foreign'])} items")
                    except Exception as e:
                        logger.error(f"Foreign collection failed: {e}")
                
                if request.dart:
                    try:
                        logger.info("Starting DART disclosure collection...")
                        results["dart"] = coll.collect_dart_disclosures(
                            insert_to_db=True
                        )
                        logger.info(f"DART collection completed: {len(results['dart'])} items")
                    except Exception as e:
                        logger.error(f"DART collection failed: {e}")
                
                total = len(results["domestic"]) + len(results["foreign"]) + len(results["dart"])
                
                logger.info(f"Background collection completed: {total} items")
                
            except Exception as e:
                logger.error(f"Collection error: {e}")
        
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


@app.get("/api/stats", tags=["Statistics"])
async def get_statistics():
    """
    Get system statistics and data collection info
    Alias for /api/collection/status for backward compatibility
    """
    return await get_collection_status()


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
