from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "AI Travel Agent"
    host: str = "0.0.0.0"
    port: int = 8000
    dev_mode: bool = True
    app_secret: str = "dev-secret-change-me"

    database_path: Path = Path("data/app.db")
    checkpoint_path: Path = Path("data/checkpoints.db")
    knowledge_dir: Path = Path("data/knowledge")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    supervisor_model: str = "deepseek-chat"
    sub_agent_model: str = "deepseek-chat"

    tavily_api_key: str = ""
    baidu_map_api_key: str = ""

    embed_provider: str = "auto"  # auto | dashscope | ollama | hash
    embed_model: str = "text-embedding-v3"
    embed_dim: int = 1024
    dashscope_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    rag_top_k: int = 4


settings = Settings()

