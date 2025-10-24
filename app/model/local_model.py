"""
Local LLM Model Handler
Handles interactions with local LLM models (using llama-cpp-python)
"""

from typing import List, Dict, Optional
from pathlib import Path
from sentence_transformers import SentenceTransformer
from loguru import logger

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python not installed. Local LLM will not work.")


class LocalModel:
    """Local LLM Handler using llama.cpp"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        n_ctx: int = 4096,
        n_threads: int = 4,
        n_gpu_layers: int = 0
    ):
        """
        Initialize Local LLM
        
        Args:
            model_path: Path to GGUF model file
            embedding_model: HuggingFace model for embeddings
            n_ctx: Context window size
            n_threads: Number of CPU threads
            n_gpu_layers: Number of layers to offload to GPU
        """
        from app.config import get_settings
        settings = get_settings()
        
        self.model_path = model_path or settings.local_model_path
        
        if not self.model_path:
            raise ValueError("Local model path is required")
        
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )
        
        # Initialize LLM
        logger.info(f"Loading local model from: {self.model_path}")
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        logger.info("Local Model initialized successfully")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        """
        Generate response using local LLM
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        """
        try:
            # Format prompt based on model type
            # (This is a generic format; adjust for specific models like Llama, Mistral, etc.)
            if system_prompt:
                full_prompt = f"""<s>[INST] <<SYS>>
{system_prompt}
<</SYS>>

{prompt} [/INST]"""
            else:
                full_prompt = f"<s>[INST] {prompt} [/INST]"
            
            response = self.llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=False,
                **kwargs
            )
            
            result = response["choices"][0]["text"].strip()
            logger.debug(f"Generated response: {result[:100]}...")
            
            return result
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def generate_with_context(
        self,
        question: str,
        context_docs: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        """
        Generate response with RAG context
        
        Args:
            question: User question
            context_docs: List of retrieved documents
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated answer
        """
        # Build context
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            etf_name = metadata.get("etf_name", "Unknown")
            date = metadata.get("date", "Unknown")
            source = metadata.get("source", "Unknown")
            
            context_parts.append(
                f"[문서 {i}] {etf_name} (날짜: {date}, 출처: {source})\n{content}\n"
            )
        
        context_text = "\n".join(context_parts)
        
        # System prompt
        system_prompt = """당신은 ETF(상장지수펀드) 투자 전문가입니다. 
주어진 문서를 바탕으로 사용자의 질문에 정확하고 유용한 답변을 제공하세요.

답변 시 주의사항:
1. 제공된 문서의 정보만을 사용하여 답변하세요
2. 확실하지 않은 정보는 추측하지 말고, 문서에 없다고 명시하세요
3. 답변의 근거가 되는 문서 번호를 [문서 N] 형태로 인용하세요
4. 투자 조언이 아닌 정보 제공에 초점을 맞추세요
5. 명확하고 구조화된 답변을 제공하세요"""
        
        prompt = f"""다음은 관련 ETF 정보입니다:

{context_text}

질문: {question}

위 문서를 참고하여 질문에 답변해주세요."""
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get text embedding using SentenceTransformer
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        try:
            embedding = self.embedding_model.encode(
                text,
                convert_to_numpy=True
            )
            
            embedding_list = embedding.tolist()
            logger.debug(f"Generated embedding with dimension: {len(embedding_list)}")
            
            return embedding_list
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.embedding_model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            embeddings_list = [emb.tolist() for emb in embeddings]
            logger.debug(f"Generated {len(embeddings_list)} embeddings")
            
            return embeddings_list
        
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise


# Example usage
if __name__ == "__main__":
    logger.info("Testing Local Model...")
    
    # Note: This requires a valid GGUF model file
    # Example: download a model from HuggingFace
    # e.g., TheBloke/Mistral-7B-Instruct-v0.2-GGUF
    
    try:
        model = LocalModel(
            model_path="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            n_gpu_layers=0  # Set > 0 if you have GPU
        )
        
        # Test generation
        response = model.generate(
            prompt="ETF란 무엇인가요?",
            temperature=0.7
        )
        print(f"Response: {response}")
        
        # Test embedding
        embedding = model.get_embedding("KODEX 200 ETF")
        print(f"Embedding dimension: {len(embedding)}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print("Note: You need to download a GGUF model file first")
