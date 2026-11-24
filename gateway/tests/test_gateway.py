from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as gateway


class Servicos:
    def __init__(self):
        self.fora_do_ar: set[str] = set()
        self.pedidos: list[httpx.Request] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if pedido.url.host in self.fora_do_ar:
            raise httpx.ConnectError("recusada", request=pedido)
        return httpx.Response(200, json={"servico": pedido.url.host, "caminho": pedido.url.path})


@pytest.fixture
def servicos(monkeypatch):
    s = Servicos()
    monkeypatch.setattr(gateway, "transporte", httpx.MockTransport(s))
    return s


@pytest.fixture
def cliente(servicos):
    with TestClient(gateway.app) as c:
        yield c


@pytest.mark.parametrize("rota,servico", [
    ("/auth/login", "usuarios"), ("/usuarios/3", "usuarios"), ("/ativos", "inventario"),
    ("/chamados/painel", "chamados"), ("/notificacoes", "notificacoes"),
])
def test_cada_rota_vai_para_o_servico_certo(cliente, rota, servico):
    assert cliente.get(rota).json() == {"servico": servico, "caminho": rota}


def test_rota_desconhecida(cliente):
    assert cliente.get("/banco/usuarios").status_code == 404


def test_repasse_do_token_e_ip(cliente, servicos):
    cliente.get("/chamados", headers={"Authorization": "Bearer abc", "Cookie": "x=1", "X-Forwarded-For": "1.2.3.4"})
    pedido = servicos.pedidos[-1]
    assert pedido.headers["authorization"] == "Bearer abc"
    assert "cookie" not in pedido.headers
    assert pedido.headers["x-forwarded-for"] != "1.2.3.4"  # não aceita IP forjado pelo cliente


def test_servico_fora_do_ar_nao_derruba_os_outros(cliente, servicos):
    servicos.fora_do_ar.add("inventario")
    r = cliente.get("/ativos")
    assert r.status_code == 503 and "inventário" in r.json()["detail"]
    assert cliente.get("/usuarios").status_code == 200
    assert cliente.get("/chamados").status_code == 200


def test_saude_mostra_cada_servico(cliente, servicos):
    assert cliente.get("/saude").json()["status"] == "ok"
    servicos.fora_do_ar.add("notificacoes")
    r = cliente.get("/saude")
    assert r.status_code == 503 and r.json()["servicos"]["notificacoes"] == "fora do ar"


def test_tela_e_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_requisicao_grande_demais(cliente):
    r = cliente.post("/chamados", content="x" * 70000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_tela_escapa_o_html():
    js = (Path(gateway.WEB) / "app.js").read_text(encoding="utf-8")
    assert "const esc =" in js and "onclick" not in js
