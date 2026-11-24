import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from comum import tokens


@pytest.fixture
def cliente(monkeypatch):
    """Banco novo, em memória, para cada teste."""
    monkeypatch.setenv("DADOS_EXEMPLO", "0")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_teste():
        with Sessao() as db:
            yield db

    app.dependency_overrides[get_db] = db_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def h():
    """Cabeçalhos de login por perfil (tokens emitidos como o serviço de Usuários faria)."""
    def cab(usuario_id, perfil):
        return {"Authorization": f"Bearer {tokens.criar(usuario_id, perfil)[0]}"}
    return {"ana": cab(2, "solicitante"), "carla": cab(4, "tecnico"), "admin": cab(1, "admin")}
