from datetime import datetime, timedelta, timezone

import jwt

from comum import config

ATIVO = {"patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}


def test_saude(cliente):
    assert cliente.get("/saude").json()["servico"] == "inventario"


def test_rotas_exigem_login(cliente):
    assert cliente.get("/ativos").status_code == 401
    assert cliente.get("/ativos/1").status_code == 401
    assert cliente.post("/ativos", json=ATIVO).status_code == 401


def test_token_de_outro_segredo_e_recusado(cliente):
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "1", "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": agora,
                        "exp": agora + timedelta(hours=1)}, "outro-segredo-com-mais-de-32-caracteres!!", algorithm="HS256")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_tecnico_cadastra_e_todos_listam(cliente, h):
    r = cliente.post("/ativos", headers=h["carla"], json=ATIVO)
    assert r.status_code == 201
    assert cliente.get(f"/ativos/{r.json()['id']}", headers=h["ana"]).json()["patrimonio"] == "PAT-1"
    assert len(cliente.get("/ativos", headers=h["ana"]).json()) == 1


def test_solicitante_nao_cadastra_ativo(cliente, h):
    assert cliente.post("/ativos", headers=h["ana"], json=ATIVO).status_code == 403


def test_patrimonio_repetido(cliente, h):
    cliente.post("/ativos", headers=h["carla"], json=ATIVO)
    assert cliente.post("/ativos", headers=h["carla"], json=ATIVO).status_code == 422


def test_campos_extras_e_invalidos(cliente, h):
    assert cliente.post("/ativos", headers=h["carla"], json={**ATIVO, "id": 99}).status_code == 422
    assert cliente.post("/ativos", headers=h["carla"], json={**ATIVO, "patrimonio": "<b>"}).status_code == 422


def test_ativo_inexistente(cliente, h):
    assert cliente.get("/ativos/999", headers=h["ana"]).status_code == 404
