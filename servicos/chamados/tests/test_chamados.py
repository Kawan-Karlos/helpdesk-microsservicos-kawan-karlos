"""Regras de negócio (as mesmas do monólito) e a conversa com os outros serviços."""
from datetime import datetime


def abrir(cliente, contas, ativo, quem="ana", prioridade="alta", **extra):
    dados = {"titulo": "PC não liga", "descricao": "Nada acontece", "prioridade": prioridade, "ativo_id": ativo["id"], **extra}
    return cliente.post("/chamados", headers=contas[quem]["headers"], json=dados)


def test_saude(cliente):
    assert cliente.get("/saude").json()["servico"] == "chamados"


def test_abrir_calcula_sla_e_publica_evento(cliente, contas, ativo, publicados):
    r = abrir(cliente, contas, ativo, prioridade="critica")
    assert r.status_code == 201
    c = r.json()
    assert c["solicitante_id"] == contas["ana"]["id"]
    horas = (datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600
    assert round(horas) == 4
    assert publicados[-1]["tipo"] == "ChamadoAberto" and publicados[-1]["destinatario_id"] == contas["ana"]["id"]


def test_sla_por_prioridade(cliente, contas, ativo):
    for prioridade, esperado in {"critica": 4, "alta": 8, "media": 24, "baixa": 72}.items():
        c = abrir(cliente, contas, ativo, prioridade=prioridade).json()
        horas = (datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600
        assert round(horas) == esperado


def test_abrir_repassa_o_token_ao_inventario(cliente, contas, ativo, outros):
    abrir(cliente, contas, ativo)
    pedido = outros.pedidos[-1]
    assert pedido.url.path == "/ativos/1"
    assert pedido.headers["authorization"] == contas["ana"]["headers"]["Authorization"]


def test_abrir_sem_equipamento_nao_chama_o_inventario(cliente, contas, ativo, outros):
    assert abrir(cliente, contas, ativo, ativo_id=None).status_code == 201
    assert outros.pedidos == []


def test_abrir_com_ativo_inexistente(cliente, contas, ativo):
    r = abrir(cliente, contas, ativo, ativo_id=999)
    assert r.status_code == 404 and r.json()["detail"] == "Ativo 999 não encontrado."


def test_atribuir_muda_status_e_avisa_tecnico(cliente, contas, ativo, publicados):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["carla"]["id"]})
    assert r.json()["status"] == "em_atendimento"
    assert publicados[-1]["tipo"] == "ChamadoAtribuido" and publicados[-1]["destinatario_id"] == contas["carla"]["id"]


def test_so_tecnico_pode_ser_atribuido(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["ana"]["id"]})
    assert r.status_code == 422


def test_atribuir_a_usuario_inexistente(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 99})
    assert r.status_code == 404


def test_fluxo_completo_de_status(cliente, contas, ativo, publicados):
    cid = abrir(cliente, contas, ativo).json()["id"]
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": contas["carla"]["id"]})
    assert cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido"}).status_code == 200
    assert publicados[-1]["tipo"] == "ChamadoResolvido"
    # o próprio solicitante confirma e fecha
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "fechado"})
    assert r.json()["status"] == "fechado"


def test_transicao_invalida(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "fechado"})
    assert r.status_code == 422


def test_iniciar_atendimento_sem_tecnico(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "em_atendimento"})
    assert r.status_code == 422


def test_comentar_usa_o_usuario_logado(cliente, contas, ativo):
    cid = abrir(cliente, contas, ativo).json()["id"]
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["carla"]["headers"], json={"texto": "Verificando a fonte."})
    assert r.status_code == 201 and r.json()["autor_id"] == contas["carla"]["id"]
    assert len(cliente.get(f"/chamados/{cid}", headers=contas["ana"]["headers"]).json()["comentarios"]) == 1


def test_painel(cliente, contas, ativo):
    abrir(cliente, contas, ativo)
    abrir(cliente, contas, ativo, prioridade="baixa")
    p = cliente.get("/chamados/painel", headers=contas["carla"]["headers"]).json()
    assert p["total"] == 2 and p["por_status"] == {"aberto": 2}


# ---------- falhas dos outros serviços ----------

def test_inventario_fora_do_ar_responde_503(cliente, contas, ativo, outros):
    outros.fora_do_ar.add("inventario")
    r = abrir(cliente, contas, ativo)
    assert r.status_code == 503 and "inventário" in r.json()["detail"]
    # a lista de chamados continua funcionando
    assert cliente.get("/chamados", headers=contas["ana"]["headers"]).status_code == 200
    # chamado sem equipamento também continua sendo aberto
    assert abrir(cliente, contas, ativo, ativo_id=None).status_code == 201


def test_inventario_lento_responde_503(cliente, contas, ativo, outros):
    outros.lentos.add("inventario")
    r = abrir(cliente, contas, ativo)
    assert r.status_code == 503 and "demorou" in r.json()["detail"]


def test_usuarios_fora_do_ar_responde_503(cliente, contas, ativo, outros):
    cid = abrir(cliente, contas, ativo).json()["id"]
    outros.fora_do_ar.add("usuarios")
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 4})
    assert r.status_code == 503 and "usuários" in r.json()["detail"]
    # e o chamado não foi alterado
    assert cliente.get(f"/chamados/{cid}", headers=contas["carla"]["headers"]).json()["status"] == "aberto"


def test_fila_fora_do_ar_nao_impede_abrir_chamado(cliente, contas, ativo, monkeypatch):
    from app import eventos
    monkeypatch.setattr(eventos, "publicados", None)
    monkeypatch.setattr(eventos, "_redis", eventos.redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2))
    assert abrir(cliente, contas, ativo).status_code == 201
