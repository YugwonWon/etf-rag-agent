"""
Model Factory - Returns the appropriate LLM model based on configuration
"""

from typing import Union, Literal
from app.config import get_settings
from app.model.openai_model import OpenAIModel
from app.model.local_model import LocalModel
from loguru import logger


ModelType = Literal["openai", "local"]


class ModelFactory:
    """Factory for creating LLM model instances"""
    
    @staticmethod
    def get_model(
        model_type: ModelType = None
    ) -> Union[OpenAIModel, LocalModel]:
        """
        Get the appropriate LLM model instance
        
        Args:
            model_type: Type of model ("openai" or "local")
                       If None, uses config setting
        
        Returns:
            Model instance (OpenAIModel or LocalModel)
        
        Raises:
            ValueError: If model type is invalid
        """
        settings = get_settings()
        model_type = model_type or settings.llm_provider
        
        logger.info(f"Initializing {model_type} model...")
        
        if model_type == "openai":
            return OpenAIModel()
        elif model_type == "local":
            return LocalModel()
        else:
            raise ValueError(
                f"Invalid model type: {model_type}. "
                f"Must be 'openai' or 'local'"
            )
    
    @staticmethod
    def create_openai_model(
        api_key: str = None,
        model: str = None
    ) -> OpenAIModel:
        """Create OpenAI model with custom parameters"""
        return OpenAIModel(api_key=api_key, model=model)
    
    @staticmethod
    def create_local_model(
        model_path: str = None,
        n_gpu_layers: int = 0
    ) -> LocalModel:
        """Create local model with custom parameters"""
        return LocalModel(model_path=model_path, n_gpu_layers=n_gpu_layers)


# Convenience function
def get_model(model_type: ModelType = None) -> Union[OpenAIModel, LocalModel]:
    """
    Convenience function to get a model instance
    
    Args:
        model_type: "openai" or "local" (uses config if None)
    
    Returns:
        Model instance
    """
    return ModelFactory.get_model(model_type)


# Example usage
if __name__ == "__main__":
    logger.info("Testing Model Factory...")
    
    try:
        # Get model based on config
        model = get_model()
        logger.info(f"Model loaded: {type(model).__name__}")
        
        # Test generation
        response = model.generate(
            prompt="ETF 투자의 장점은 무엇인가요?",
            temperature=0.7
        )
        print(f"\nResponse:\n{response}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
