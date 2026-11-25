import os
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

    # Redis: 登录验证码、token、短期对话记忆
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_fake: bool = False
    short_term_max_messages: int = 12
    short_term_keep_messages: int = 6
    short_term_ttl: int = 7 * 24 * 3600
    short_term_summary_chars: int = 1200

    # RAG 后端：sqlite（零依赖兜底）| milvus
    rag_backend: str = "sqlite"
    milvus_uri: str = "http://127.0.0.1:19530"
    milvus_collection: str = "travel_kb"

    # LangSmith 可选可观测性
    langsmith_api_key: str = ""
    langsmith_project: str = "ai-travel-agent"


settings = Settings()

if settings.langsmith_api_key:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    # 兼容旧版 LangChain 环境变量
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
