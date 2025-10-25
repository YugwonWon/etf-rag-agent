"""
Configuration Management for ETF RAG Agent
Loads environment variables and provides centralized config access
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application Settings"""
    
    # LLM Configuration
    llm_provider: Literal["openai", "local"] = Field(default="openai", env="LLM_PROVIDER")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_timeout: int = Field(default=25, env="OPENAI_TIMEOUT")  # API 호출 타임아웃 (초)
    
    # Local LLM
    local_model_path: Optional[str] = Field(default=None, env="LOCAL_MODEL_PATH")
    local_model_type: str = Field(default="qwen2.5:3b", env="LOCAL_MODEL_TYPE")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_api_key: Optional[str] = Field(default=None, env="OLLAMA_API_KEY")
    
    # Weaviate
    weaviate_url: str = Field(default="http://localhost:8080", env="WEAVIATE_URL")
    weaviate_api_key: Optional[str] = Field(default=None, env="WEAVIATE_API_KEY")
    weaviate_class_name: str = Field(default="ETFDocument", env="WEAVIATE_CLASS_NAME")
    
    # DART API
    dart_api_key: Optional[str] = Field(default=None, env="DART_API_KEY")
    
    # Crawler
    naver_etf_list_url: str = Field(
        default="https://finance.naver.com/sise/etf.naver",
        env="NAVER_ETF_LIST_URL"
    )
    use_selenium: bool = Field(default=False, env="USE_SELENIUM")
    chromedriver_path: Optional[str] = Field(default=None, env="CHROMEDRIVER_PATH")
    
    # Scheduler
    crawl_time_hour: int = Field(default=9, env="CRAWL_TIME_HOUR")
    crawl_time_minute: int = Field(default=0, env="CRAWL_TIME_MINUTE")
    enable_scheduler: bool = Field(default=True, env="ENABLE_SCHEDULER")
    run_initial_collection: bool = Field(default=False, env="RUN_INITIAL_COLLECTION")  # 서버 시작 시 즉시 실행 여부
    collect_only_outdated: bool = Field(default=True, env="COLLECT_ONLY_OUTDATED")  # 최근 N일 이내 업데이트 안 된 것만 수집
    update_threshold_days: int = Field(default=7, env="UPDATE_THRESHOLD_DAYS")  # 갱신 기준 일수
    
    # Data Collection Limits
    max_domestic_etfs: Optional[int] = Field(default=None, env="MAX_DOMESTIC_ETFS")  # 국내 ETF 최대 수집 개수
    max_foreign_etfs: Optional[int] = Field(default=None, env="MAX_FOREIGN_ETFS")  # 해외 ETF 최대 수집 개수
    max_dart_docs: Optional[int] = Field(default=None, env="MAX_DART_DOCS")  # DART 공시 최대 수집 개수
    
    # Server
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    grpc_host: str = Field(default="0.0.0.0", env="GRPC_HOST")
    grpc_port: int = Field(default=50051, env="GRPC_PORT")
    
    # Data Storage
    data_dir: Path = Field(default=Path("./data"), env="DATA_DIR")
    raw_data_dir: Path = Field(default=Path("./data/raw"), env="RAW_DATA_DIR")
    metadata_file: Path = Field(default=Path("./data/metadata.json"), env="METADATA_FILE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Path = Field(default=Path("./logs/etf-rag-agent.log"), env="LOG_FILE")
    
    # RAG Configuration
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    enable_cache: bool = Field(default=False, env="ENABLE_CACHE")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    rag_top_k: int = Field(default=5, env="RAG_TOP_K")
    rag_temperature: float = Field(default=0.7, env="RAG_TEMPERATURE")
    rag_max_tokens: int = Field(default=2000, env="RAG_MAX_TOKENS")
    
    # Embedding Configuration
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=1536, env="EMBEDDING_DIM")
    
    # Version Control
    enable_duplicate_check: bool = Field(default=True, env="ENABLE_DUPLICATE_CHECK")
    keep_history: bool = Field(default=True, env="KEEP_HISTORY")
    max_versions_per_etf: int = Field(default=10, env="MAX_VERSIONS_PER_ETF")
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    reload: bool = Field(default=False, env="RELOAD")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    
    # Application Settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    project_name: str = Field(default="ETF RAG Agent", env="PROJECT_NAME")
    timezone: str = Field(default="Asia/Seoul", env="TIMEZONE")
    profiling: bool = Field(default=False, env="PROFILING")
    
    # Gradio Settings
    gradio_port: int = Field(default=7860, env="GRADIO_PORT")
    
    # Hugging Face Settings
    hf_token: Optional[str] = Field(default=None, env="HF_TOKEN")
    hf_space: Optional[str] = Field(default=None, env="HF_SPACE")
    
    @validator("data_dir", "raw_data_dir", pre=True)
    def convert_to_path(cls, v):
        """Convert string to Path object"""
        if isinstance(v, str):
            return Path(v)
        return v
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
settings.ensure_directories()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def validate_config():
    """Validate configuration based on selected provider"""
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set when LLM_PROVIDER is 'openai'"
            )
    elif settings.llm_provider == "local":
        if not settings.local_model_path:
            raise ValueError(
                "LOCAL_MODEL_PATH must be set when LLM_PROVIDER is 'local'"
            )
        if not Path(settings.local_model_path).exists():
            raise FileNotFoundError(
                f"Local model file not found: {settings.local_model_path}"
            )
    
    # Validate DART API key if needed
    # (Optional: can be added later when implementing DART crawler)
    
    return True


if __name__ == "__main__":
    # Test configuration
    print("=== ETF RAG Agent Configuration ===")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Weaviate URL: {settings.weaviate_url}")
    print(f"Data Directory: {settings.data_dir}")
    print(f"Scheduler Enabled: {settings.enable_scheduler}")
    print(f"API Port: {settings.api_port}")
    print(f"gRPC Port: {settings.grpc_port}")
    
    try:
        validate_config()
        print("\n✓ Configuration is valid")
    except Exception as e:
        print(f"\n✗ Configuration error: {e}")
