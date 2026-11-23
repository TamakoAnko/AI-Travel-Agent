# Backend image: FastAPI + LangGraph + SQLite + local RAG
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY data ./data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "ai_travel_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
