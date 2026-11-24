"""Monta a aplicação FastAPI de um serviço, já com as proteções comuns e o /saude."""
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from comum import erros
from comum.config import DOCS_ATIVA
from comum.seguranca_http import CabecalhosDeSeguranca


def criar_app(nome: str, lifespan=None) -> FastAPI:
    app = FastAPI(
        title=f"HelpDesk TI · {nome}", version="3.0.0", lifespan=lifespan,
        docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
        openapi_url="/openapi.json" if DOCS_ATIVA else None,
    )
    app.add_middleware(CabecalhosDeSeguranca)
    erros.registrar(app)

    @app.get("/saude", tags=["Saúde"])
    def saude():
        return {"status": "ok", "servico": nome}

    return app


def conectar(url: str):
    """Cria a conexão com o banco DESTE serviço."""
    engine = create_engine(
        url, pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
