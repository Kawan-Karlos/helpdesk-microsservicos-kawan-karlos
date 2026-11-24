"""Publicação de eventos na fila (Redis).

O serviço de Chamados não sabe quem vai consumir os eventos: só os coloca na
fila. O serviço de Notificações lê a fila e grava os avisos.

Publicar é "melhor esforço": se o Redis estiver fora do ar, o chamado é salvo
do mesmo jeito e só o aviso se perde (fica registrado no log). Se o serviço de
Notificações cair, os eventos esperam na fila até ele voltar.
"""
import json
import logging
import os
from datetime import datetime

import redis

log = logging.getLogger("helpdesk.chamados")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FILA = "helpdesk:eventos"

_redis = redis.Redis.from_url(REDIS_URL, socket_timeout=1, socket_connect_timeout=1)

# Nos testes, guardamos os eventos aqui em vez de mandar para o Redis
publicados: list[dict] | None = None


def publicar(tipo: str, destinatario_id: int, mensagem: str, chamado_id: int) -> None:
    evento = {
        "tipo": tipo, "destinatario_id": destinatario_id, "mensagem": mensagem,
        "chamado_id": chamado_id, "ocorrido_em": datetime.now().isoformat(),
    }
    if publicados is not None:
        publicados.append(evento)
        return
    try:
        _redis.lpush(FILA, json.dumps(evento))
    except redis.RedisError as erro:
        log.warning("Não foi possível publicar o evento %s do chamado #%s: %s", tipo, chamado_id, erro)
