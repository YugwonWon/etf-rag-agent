"""
ConnectRPC gRPC Server Implementation
"""

from concurrent import futures
import grpc
from loguru import logger

# Import generated proto files (generated after running protoc)
# These will be generated using: python -m grpc_tools.protoc
try:
    from protos.__generated__ import etf_query_pb2
    from protos.__generated__ import etf_query_pb2_grpc
except ImportError:
    logger.warning(
        "Proto files not generated yet. Run: "
        "python -m grpc_tools.protoc -I./protos --python_out=./protos/__generated__ "
        "--grpc_python_out=./protos/__generated__ ./protos/etf_query.proto"
    )
    etf_query_pb2 = None
    etf_query_pb2_grpc = None

from app.config import get_settings
from app.retriever.query_handler import RAGQueryHandler
from app.vector_store.weaviate_handler import WeaviateHandler
from app.crawler.collector import ETFDataCollector


class ETFQueryServicer:
    """gRPC Servicer implementation"""
    
    def __init__(self):
        """Initialize servicer"""
        self.settings = get_settings()
        self.rag_handler = None
        self.vector_handler = None
        self.collector = None
        
        logger.info("ETF Query Servicer initialized")
    
    def _ensure_rag_handler(self, model_type: str = None):
        """Lazily initialize RAG handler"""
        if self.rag_handler is None or (model_type and self.rag_handler.model_type != model_type):
            if self.vector_handler is None:
                self.vector_handler = WeaviateHandler()
            
            self.rag_handler = RAGQueryHandler(
                vector_handler=self.vector_handler,
                model_type=model_type or self.settings.llm_provider
            )
    
    def _ensure_collector(self):
        """Lazily initialize collector"""
        if self.collector is None:
            if self.vector_handler is None:
                self.vector_handler = WeaviateHandler()
            
            self.collector = ETFDataCollector(
                vector_handler=self.vector_handler,
                model_type=self.settings.llm_provider
            )
    
    def AskQuestion(self, request, context):
        """Handle question answering"""
        try:
            logger.info(f"Received question: {request.question}")
            
            # Initialize handler
            model_type = request.model_type or self.settings.llm_provider
            self._ensure_rag_handler(model_type)
            
            # Prepare filters
            filters = {}
            if request.etf_type:
                filters["etf_type"] = request.etf_type
            
            # Query
            response = self.rag_handler.query(
                question=request.question,
                top_k=request.top_k if request.top_k > 0 else None,
                filters=filters if filters else None,
                temperature=request.temperature if request.temperature > 0 else 0.7
            )
            
            # Build proto response
            sources = [
                etf_query_pb2.Source(
                    rank=src["rank"],
                    etf_name=src["etf_name"],
                    etf_code=src["etf_code"],
                    source=src["source"],
                    date=src["date"],
                    relevance=src["relevance"],
                    preview=src["preview"]
                )
                for src in response["sources"]
            ]
            
            return etf_query_pb2.AnswerResponse(
                answer=response["answer"],
                sources=sources,
                num_sources=response["num_sources"],
                model_type=response["model_type"]
            )
        
        except Exception as e:
            logger.error(f"Error in AskQuestion: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return etf_query_pb2.AnswerResponse()
    
    def GetETFSummary(self, request, context):
        """Get ETF summary"""
        try:
            logger.info(f"Getting summary for: {request.etf_code}")
            
            self._ensure_rag_handler()
            
            summary = self.rag_handler.get_etf_summary(request.etf_code)
            
            if not summary:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"ETF not found: {request.etf_code}")
                return etf_query_pb2.ETFSummaryResponse()
            
            return etf_query_pb2.ETFSummaryResponse(
                etf_code=summary["etf_code"],
                etf_name=summary["etf_name"],
                etf_type=summary["etf_type"],
                category=summary["category"],
                source=summary["source"],
                last_updated=summary["last_updated"],
                content_preview=summary["content_preview"],
                num_versions=summary["num_versions"]
            )
        
        except Exception as e:
            logger.error(f"Error in GetETFSummary: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return etf_query_pb2.ETFSummaryResponse()
    
    def TriggerCollection(self, request, context):
        """Trigger manual data collection"""
        try:
            logger.info("Manual collection triggered")
            
            self._ensure_collector()
            
            # Determine what to collect
            collect_domestic = request.domestic if request.HasField("domestic") else True
            collect_foreign = request.foreign if request.HasField("foreign") else True
            collect_dart = request.dart if request.HasField("dart") else True
            
            results = {
                "domestic": [],
                "foreign": [],
                "dart": []
            }
            
            # Collect data
            if collect_domestic:
                results["domestic"] = self.collector.collect_domestic_etfs(
                    max_items=request.domestic_max if request.domestic_max > 0 else None,
                    insert_to_db=True
                )
            
            if collect_foreign:
                results["foreign"] = self.collector.collect_foreign_etfs(
                    insert_to_db=True
                )
            
            if collect_dart:
                results["dart"] = self.collector.collect_dart_disclosures(
                    insert_to_db=True
                )
            
            total = len(results["domestic"]) + len(results["foreign"]) + len(results["dart"])
            
            return etf_query_pb2.CollectionResponse(
                success=True,
                message=f"Collection completed successfully",
                domestic_count=len(results["domestic"]),
                foreign_count=len(results["foreign"]),
                dart_count=len(results["dart"]),
                total_count=total
            )
        
        except Exception as e:
            logger.error(f"Error in TriggerCollection: {e}")
            return etf_query_pb2.CollectionResponse(
                success=False,
                message=f"Collection failed: {str(e)}",
                domestic_count=0,
                foreign_count=0,
                dart_count=0,
                total_count=0
            )
    
    def HealthCheck(self, request, context):
        """Health check"""
        try:
            if self.vector_handler is None:
                self.vector_handler = WeaviateHandler()
            
            doc_count = self.vector_handler.get_document_count()
            
            return etf_query_pb2.HealthResponse(
                healthy=True,
                status="OK",
                version="0.1.0",
                total_documents=doc_count
            )
        
        except Exception as e:
            logger.error(f"Error in HealthCheck: {e}")
            return etf_query_pb2.HealthResponse(
                healthy=False,
                status=f"ERROR: {str(e)}",
                version="0.1.0",
                total_documents=0
            )


def serve(port: int = None):
    """Start gRPC server"""
    if etf_query_pb2_grpc is None:
        logger.error("Proto files not generated. Cannot start gRPC server.")
        return
    
    settings = get_settings()
    port = port or settings.grpc_port
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    servicer = ETFQueryServicer()
    etf_query_pb2_grpc.add_ETFQueryServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    
    logger.info(f"gRPC server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Stopping gRPC server...")
        server.stop(0)


if __name__ == "__main__":
    logger.info("Starting ConnectRPC server...")
    serve()
