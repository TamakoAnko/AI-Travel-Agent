"""CLI entry points: serve and knowledge-base ingestion."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-travel-agent")
    sub = parser.add_subparsers(dest="command")
    ingest = sub.add_parser("ingest", help="构建/重建 RAG 知识库索引")
    ingest.add_argument("--reset", action="store_true", help="清空旧索引后重建")
    serve = sub.add_parser("serve", help="启动 FastAPI 服务")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    if args.command == "ingest":
        from . import db
        from .rag import get_kb

        db.init_db()
        count = get_kb().ensure_seed(reset=args.reset)
        print(f"知识库索引完成：{count} 个片段")
        return

    import uvicorn
    from .config import settings

    uvicorn.run(
        "ai_travel_agent.api:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=args.command is None,
    )
