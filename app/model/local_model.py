"""
Local LLM Model Handler
Handles interactions with local LLM models (using Ollama)
"""

from typing import List, Dict, Optional
from pathlib import Path
from sentence_transformers import SentenceTransformer
from loguru import logger
import requests
import json


class LocalModel:
    """Local LLM Handler using Ollama"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        ollama_url: str = "http://localhost:11434"
    ):
        """
        Initialize Local LLM with Ollama
        
        Args:
            model_name: Ollama model name (e.g., 'qwen2.5:3b')
            embedding_model: HuggingFace model for embeddings
            ollama_url: Ollama API URL
        """
        from app.config import get_settings
        settings = get_settings()
        
        self.model_name = model_name or settings.local_model_type or "qwen2.5:3b"
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        self.ollama_available = False  # Initialize as False
        
        # Test Ollama connection
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.ollama_available = True  # Set to True on success
                logger.info(f"Connected to Ollama at {ollama_url}")
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                logger.info(f"Available models: {model_names}")
                
                if not any(self.model_name in name for name in model_names):
                    logger.warning(f"Model {self.model_name} not found. Please run: ollama pull {self.model_name}")
                    self.ollama_available = False  # Model not found
            else:
                logger.warning(f"Failed to connect to Ollama: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}. Make sure Ollama is running.")
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        logger.info(f"Local Model initialized with Ollama model: {self.model_name}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate response using Ollama
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        """
        try:
            # Check if Ollama is available
            if not self.ollama_available:
                logger.warning("Ollama not available, returning context-based summary")
                # Return a simple summary from the prompt
                return self._generate_simple_summary(prompt)
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make API request
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json().get("response", "").strip()
            logger.debug(f"Generated response: {result[:100]}...")
            
            return result
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Fallback to simple summary
            return self._generate_simple_summary(prompt)
    
    def _generate_simple_summary(self, prompt: str) -> str:
        """
        Generate a simple summary when Ollama is not available
        
        Args:
            prompt: The prompt containing context and question
        
        Returns:
            Simple formatted summary of the context
        """
        # Extract context documents from prompt
        lines = prompt.split('\n')
        
        summary_parts = []
        summary_parts.append("**제공된 정보를 기반으로 한 요약:**\n")
        
        # Find document sections
        doc_sections = []
        current_doc = []
        for line in lines:
            if line.startswith('[문서'):
                if current_doc:
                    doc_sections.append('\n'.join(current_doc))
                current_doc = [line]
            elif current_doc:
                current_doc.append(line)
        
        if current_doc:
            doc_sections.append('\n'.join(current_doc))
        
        # Add document summaries
        for i, doc_section in enumerate(doc_sections[:3], 1):  # Max 3 documents
            # Extract first 200 characters of each document
            doc_lines = doc_section.split('\n')
            if doc_lines:
                header = doc_lines[0]
                content = ' '.join(doc_lines[1:])[:300]
                summary_parts.append(f"\n{header}")
                summary_parts.append(f"{content}...\n")
        
        summary_parts.append("\n💡 **참고**: 더 상세한 답변을 위해서는 Ollama 서버를 실행해주세요.")
        summary_parts.append("자세한 설치 방법: https://ollama.ai/")
        
        return '\n'.join(summary_parts)
    
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
