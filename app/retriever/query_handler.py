"""
RAG Query Handler
Handles question answering using retrieval-augmented generation
"""

from typing import List, Dict, Optional
from loguru import logger

from app.config import get_settings
from app.vector_store.weaviate_handler import WeaviateHandler
from app.model.model_factory import get_model, ModelType


class RAGQueryHandler:
    """Handler for RAG-based question answering"""
    
    def __init__(
        self,
        vector_handler: Optional[WeaviateHandler] = None,
        model_type: ModelType = None
    ):
        """
        Initialize RAG handler
        
        Args:
            vector_handler: WeaviateHandler instance
            model_type: LLM model type ("openai" or "local")
        """
        self.settings = get_settings()
        
        # Initialize vector handler
        if vector_handler:
            self.vector_handler = vector_handler
        else:
            self.vector_handler = WeaviateHandler()
        
        # Initialize LLM model
        self.model_type = model_type or self.settings.llm_provider
        self.model = get_model(self.model_type)
        
        logger.info(f"RAG Handler initialized with {self.model_type} model")
    
    def query(
        self,
        question: str,
        top_k: int = None,
        filters: Optional[Dict[str, str]] = None,
        temperature: float = 0.7
    ) -> Dict[str, any]:
        """
        Answer question using RAG
        
        Args:
            question: User question
            top_k: Number of documents to retrieve
            filters: Filter conditions (e.g., {"etf_type": "domestic"})
            temperature: LLM temperature
        
        Returns:
            Answer dict with response, sources, and metadata
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Get top_k from settings if not specified
            if top_k is None:
                top_k = self.settings.top_k_results
            
            # Step 1: Generate query embedding
            logger.debug("Generating query embedding...")
            query_vector = self.model.get_embedding(question)
            
            # Step 2: Retrieve relevant documents
            logger.debug(f"Retrieving top {top_k} documents...")
            results = self.vector_handler.search(
                query_vector=query_vector,
                limit=top_k,
                filters=filters,
                min_certainty=self.settings.similarity_threshold
            )
            
            if not results:
                logger.warning("No relevant documents found")
                return {
                    "answer": "죄송합니다. 질문과 관련된 ETF 정보를 찾을 수 없습니다.",
                    "sources": [],
                    "num_sources": 0,
                    "model_type": self.model_type
                }
            
            logger.info(f"Retrieved {len(results)} relevant documents")
            
            # Step 3: Format context documents
            context_docs = []
            for result in results:
                context_docs.append({
                    "content": result["content"],
                    "metadata": result["metadata"]
                })
            
            # Step 4: Generate answer using LLM
            logger.debug("Generating answer...")
            answer = self.model.generate_with_context(
                question=question,
                context_docs=context_docs,
                temperature=temperature
            )
            
            # Step 5: Format response
            sources = []
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                sources.append({
                    "rank": i,
                    "etf_name": metadata.get("etf_name", "Unknown"),
                    "etf_code": metadata.get("etf_code", ""),
                    "source": metadata.get("source", ""),
                    "date": metadata.get("date", ""),
                    "relevance": result.get("certainty", 0),
                    "preview": result["content"][:200] + "..."
                })
            
            response = {
                "answer": answer,
                "sources": sources,
                "num_sources": len(sources),
                "model_type": self.model_type,
                "question": question
            }
            
            logger.info("Query processed successfully")
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise
    
    def query_domestic_only(
        self,
        question: str,
        top_k: int = None,
        temperature: float = 0.7
    ) -> Dict[str, any]:
        """Query domestic ETFs only"""
        return self.query(
            question=question,
            top_k=top_k,
            filters={"etf_type": "domestic"},
            temperature=temperature
        )
    
    def query_foreign_only(
        self,
        question: str,
        top_k: int = None,
        temperature: float = 0.7
    ) -> Dict[str, any]:
        """Query foreign ETFs only"""
        return self.query(
            question=question,
            top_k=top_k,
            filters={"etf_type": "foreign"},
            temperature=temperature
        )
    
    def query_specific_etf(
        self,
        etf_code: str,
        question: str,
        temperature: float = 0.7
    ) -> Dict[str, any]:
        """Query about a specific ETF"""
        return self.query(
            question=question,
            filters={"etf_code": etf_code},
            top_k=5,
            temperature=temperature
        )
    
    def get_etf_summary(
        self,
        etf_code: str
    ) -> Optional[Dict[str, any]]:
        """
        Get comprehensive summary of an ETF
        
        Args:
            etf_code: ETF code or ticker
        
        Returns:
            Summary dict with key information
        """
        try:
            # Get all documents for this ETF
            dummy_vector = [0.0] * 1536  # Dummy vector for search
            
            results = self.vector_handler.search(
                query_vector=dummy_vector,
                limit=10,
                filters={"etf_code": etf_code},
                min_certainty=0.0  # Get all versions
            )
            
            if not results:
                return None
            
            # Use most recent version
            latest = results[0]
            metadata = latest["metadata"]
            
            summary = {
                "etf_code": etf_code,
                "etf_name": metadata.get("etf_name", "Unknown"),
                "etf_type": metadata.get("etf_type", "Unknown"),
                "category": metadata.get("category", "Unknown"),
                "source": metadata.get("source", "Unknown"),
                "last_updated": metadata.get("date", "Unknown"),
                "content_preview": latest["content"][:500] + "...",
                "num_versions": len(results)
            }
            
            return summary
        
        except Exception as e:
            logger.error(f"Error getting ETF summary: {e}")
            return None
    
    def close(self):
        """Clean up resources"""
        if self.vector_handler:
            self.vector_handler.close()


# Example usage
if __name__ == "__main__":
    logger.info("Testing RAG Query Handler...")
    
    try:
        # Initialize handler
        handler = RAGQueryHandler(model_type="openai")
        
        # Test queries
        test_questions = [
            "KODEX 미국S&P500 ETF의 특징은 무엇인가요?",
            "SPY ETF의 보수율은 얼마인가요?",
            "환헤지 ETF 추천해주세요"
        ]
        
        for question in test_questions:
            print(f"\n질문: {question}")
            print("-" * 60)
            
            response = handler.query(question)
            
            print(f"\n답변:\n{response['answer']}\n")
            print(f"참고 문서 ({response['num_sources']}개):")
            for source in response['sources'][:3]:
                print(f"  [{source['rank']}] {source['etf_name']} "
                      f"(관련도: {source['relevance']:.2f})")
        
        handler.close()
    
    except Exception as e:
        logger.error(f"Error: {e}")
