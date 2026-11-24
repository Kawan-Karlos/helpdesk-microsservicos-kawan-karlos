import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import consumidor
from app.database import Base, get_db
from app.main import app
from comum import tokens


@pytest.fixture
def Sessao(monkeypatch):
    monkeypatch.setenv("CONSUMIR_FILA", "0")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def cliente(Sessao):
    def db_de_teste():
        with Sessao() as db:
            yield db
    app.dependency_overrides[get_db] = db_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def cab(usuario_id, perfil="solicitante"):
    return {"Authorization": f"Bearer {tokens.criar(usuario_id, perfil)[0]}"}


def evento(tipo="ChamadoAberto", destinatario_id=2):
    return json.dumps({"tipo": tipo, "destinatario_id": destinatario_id, "mensagem": "Seu chamado #1 foi aberto.", "chamado_id": 1})


def test_saude(cliente):
    assert cliente.get("/saude").json()["servico"] == "notificacoes"


def test_exige_login(cliente):
    assert cliente.get("/notificacoes").status_code == 401


def test_evento_vira_notificacao(cliente, Sessao):
    consumidor.gravar(Sessao, evento())
    avisos = cliente.get("/notificacoes", headers=cab(2)).json()
    assert len(avisos) == 1 and avisos[0]["tipo"] == "ChamadoAberto"


def test_notificacoes_sao_so_do_proprio_usuario(cliente, Sessao):
    consumidor.gravar(Sessao, evento(destinatario_id=2))
    assert cliente.get("/notificacoes", headers=cab(3)).json() == []


def test_evento_invalido_e_ignorado(Sessao):
    assert consumidor.gravar(Sessao, "isto não é json") is None
    assert consumidor.gravar(Sessao, evento(tipo="ApagarTudo")) is None
    assert consumidor.gravar(Sessao, json.dumps({"tipo": "ChamadoAberto"})) is None
