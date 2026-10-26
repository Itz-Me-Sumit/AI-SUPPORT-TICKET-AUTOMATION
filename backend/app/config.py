from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# OPENROUTER_API_KEY ko os.environ mein load karta hai (ChatOpenRouter yahin se padhta hai)
load_dotenv()


class Settings(BaseSettings):
    llm_model: str = "openrouter/free"
    llm_temperature: float = 0.1
    llm_max_retries: int = 3

    # Voice helpdesk and RAG
    voice_api_secret: str = ""
    voice_llm_model: str = ""
    knowledge_dir: str = "knowledge"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: str = "./data/fastembed_cache"
    rag_top_k: int = 3
    rag_min_score: float = 0.35

    database_url: str = "sqlite:///./data/tickets.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
