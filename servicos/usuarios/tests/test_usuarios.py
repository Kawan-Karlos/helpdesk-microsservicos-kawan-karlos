"""Testes do serviço de Usuários, incluindo os de segurança do login e do token."""
from datetime import datetime, timedelta, timezone

import jwt

from app import limite
from app.modelos import Usuario
from comum import config

SENHA = "Senha123"


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "usuarios"}


def test_rotas_exigem_login(cliente, contas):
    for rota in ("/usuarios", "/usuarios/1", "/auth/eu"):
        assert cliente.get(rota).status_code == 401, rota


def test_login_e_quem_sou_eu(cliente, contas):
    r = cliente.get("/auth/eu", headers=contas["ana"]["headers"])
    assert r.status_code == 200 and r.json()["email"] == "ana@x.com"


def test_login_com_senha_errada(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_login_com_email_inexistente_tem_a_mesma_mensagem(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ninguem@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_bloqueio_apos_varias_senhas_erradas(cliente, contas):
    for _ in range(limite.LOGIN_MAX_FALHAS):
        cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    assert cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA}).status_code == 429


def _token(segredo, sub, quando=None, alg="HS256", **extra):
    agora = quando or datetime.now(timezone.utc)
    dados = {"sub": str(sub), "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": agora,
             "exp": agora + timedelta(hours=1), **extra}
    return jwt.encode(dados, segredo, algorithm=alg)


def test_token_adulterado(cliente, contas):
    token = contas["ana"]["headers"]["Authorization"] + "x"
    assert cliente.get("/auth/eu", headers={"Authorization": token}).status_code == 401


def test_token_assinado_com_outro_segredo(cliente, contas):
    falso = _token("segredo-de-outra-pessoa-com-mais-de-32-caracteres", contas["admin"]["id"])
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente, contas):
    falso = _token(None, contas["admin"]["id"], alg="none")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente, contas):
    vencido = _token(config.JWT_SEGREDO, contas["ana"]["id"], quando=datetime.now(timezone.utc) - timedelta(hours=2))
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_senha_guardada_com_hash(sessao, contas):
    with sessao() as db:
        u = db.query(Usuario).filter_by(email="ana@x.com").one()
        assert SENHA not in u.senha_hash and u.senha_hash.startswith("scrypt$")


def test_admin_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "tecnico", "senha": "Forte1234"})
    assert r.status_code == 201 and "senha" not in r.json()


def test_senha_fraca_e_recusada(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "solicitante", "senha": "abcdefgh"})
    assert r.status_code == 422


def test_email_repetido(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Outra Ana", "email": "ana@x.com", "perfil": "solicitante", "senha": "Forte1234"})
    assert r.status_code == 422


def test_solicitante_nao_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["ana"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "admin", "senha": "Forte1234"})
    assert r.status_code == 403


def test_lista_nao_mostra_email(cliente, contas):
    lista = cliente.get("/usuarios", headers=contas["ana"]["headers"]).json()
    assert len(lista) == 3 and all("email" not in u for u in lista)


def test_obter_usuario_por_id(cliente, contas):
    r = cliente.get(f"/usuarios/{contas['carla']['id']}", headers=contas["ana"]["headers"])
    assert r.json()["perfil"] == "tecnico"
    assert cliente.get("/usuarios/999", headers=contas["ana"]["headers"]).status_code == 404


def test_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/saude")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
