"""
OpenAI Model Handler
Handles interactions with OpenAI GPT models
"""

from typing import List, Dict, Optional
from openai import OpenAI
from app.config import get_settings
from loguru import logger


class OpenAIModel:
    """OpenAI GPT Model Handler"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key (if None, uses config)
            model: Model name (if None, uses config)
        """
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.embedding_model = settings.openai_embedding_model
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"OpenAI Model initialized: {self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate response using OpenAI Chat Completion
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for OpenAI API
        
        Returns:
            Generated text response
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            result = response.choices[0].message.content
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
            context_docs: List of retrieved documents with 'content' and 'metadata'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated answer with citations
        """
        # Build context from retrieved documents
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
        
        # System prompt for RAG
        system_prompt = """당신은 ETF(상장지수펀드) 투자 전문가입니다. 
주어진 문서를 바탕으로 사용자의 질문에 정확하고 유용한 답변을 제공하세요.

답변 시 주의사항:
1. 제공된 문서의 정보만을 사용하여 답변하세요
2. 확실하지 않은 정보는 추측하지 말고, 문서에 없다고 명시하세요
3. 답변의 근거가 되는 문서 번호를 [문서 N] 형태로 인용하세요
4. 투자 조언이 아닌 정보 제공에 초점을 맞추세요
5. 명확하고 구조화된 답변을 제공하세요"""
        
        # User prompt with context
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
        Get text embedding using OpenAI Embeddings API
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (list of floats)
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with dimension: {len(embedding)}")
            
            return embedding
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings")
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise


# Example usage
if __name__ == "__main__":
    from loguru import logger
    
    logger.info("Testing OpenAI Model...")
    
    try:
        model = OpenAIModel()
        
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
