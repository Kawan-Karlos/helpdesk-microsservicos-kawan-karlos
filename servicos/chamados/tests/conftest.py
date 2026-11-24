"""Os serviços de Usuários e Inventário são simulados com httpx.MockTransport:
o código de rede de verdade (app.clientes) roda, só a resposta é falsa."""
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import clientes, eventos
from app.database import Base, get_db
from app.main import app
from comum import tokens

USUARIOS = {1: "admin", 2: "solicitante", 3: "solicitante", 4: "tecnico"}
ATIVOS = {1}


class OutrosServicos:
    """Finge ser os serviços de Usuários e Inventário."""

    def __init__(self):
        self.fora_do_ar: set[str] = set()
        self.lentos: set[str] = set()
        self.pedidos: list[httpx.Request] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        servico = pedido.url.host
        if servico in self.fora_do_ar:
            raise httpx.ConnectError("conexão recusada", request=pedido)
        if servico in self.lentos:
            raise httpx.ReadTimeout("tempo esgotado", request=pedido)
        if not pedido.headers.get("authorization", "").startswith("Bearer "):
            return httpx.Response(401)
        _, recurso, ident = pedido.url.path.split("/")
        ident = int(ident)
        if recurso == "usuarios" and ident in USUARIOS:
            return httpx.Response(200, json={"id": ident, "nome": f"Pessoa {ident}", "perfil": USUARIOS[ident]})
        if recurso == "ativos" and ident in ATIVOS:
            return httpx.Response(200, json={"id": ident, "patrimonio": "PAT-1", "tipo": "computador",
                                             "descricao": "Desktop", "setor": "TI"})
        return httpx.Response(404, json={"detail": "não encontrado"})


@pytest.fixture
def outros(monkeypatch):
    falso = OutrosServicos()
    monkeypatch.setattr(clientes, "transporte", httpx.MockTransport(falso))
    return falso


@pytest.fixture
def publicados(monkeypatch):
    lista: list[dict] = []
    monkeypatch.setattr(eventos, "publicados", lista)
    return lista


@pytest.fixture
def cliente(monkeypatch, outros, publicados):
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
def contas():
    def conta(usuario_id):
        token = tokens.criar(usuario_id, USUARIOS[usuario_id])[0]
        return {"headers": {"Authorization": f"Bearer {token}"}, "id": usuario_id}
    return {"admin": conta(1), "ana": conta(2), "bia": conta(3), "carla": conta(4)}


@pytest.fixture
def ativo():
    return {"id": 1}
