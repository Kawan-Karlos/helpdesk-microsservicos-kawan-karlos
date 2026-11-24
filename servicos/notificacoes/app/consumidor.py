"""Lê os eventos da fila (Redis) e grava as notificações.

Roda em uma thread separada. Se o Redis cair, espera e tenta de novo.
Se este serviço cair, os eventos ficam na fila e são lidos quando ele voltar.
"""
import json
import logging
import os
import threading
import time
from datetime import datetime

import redis
from sqlalchemy.orm import sessionmaker

from app.database import Notificacao

log = logging.getLogger("helpdesk.notificacoes")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FILA = "helpdesk:eventos"
TIPOS = {"ChamadoAberto", "ChamadoAtribuido", "ChamadoResolvido"}


def gravar(Sessao: sessionmaker, bruto: bytes | str) -> Notificacao | None:
    """Transforma um evento em notificação. Eventos estranhos são ignorados."""
    try:
        evento = json.loads(bruto)
        if evento["tipo"] not in TIPOS:
            raise ValueError(f"tipo desconhecido: {evento['tipo']}")
        aviso = Notificacao(tipo=evento["tipo"], destinatario_id=int(evento["destinatario_id"]),
                            mensagem=str(evento["mensagem"])[:300], criada_em=datetime.now())
    except (ValueError, KeyError, TypeError) as erro:
        log.warning("Evento inválido descartado: %s", erro)
        return None
    with Sessao() as db:
        db.add(aviso)
        db.commit()
        db.refresh(aviso)
    log.info("Notificação gravada: %s para o usuário %s", aviso.tipo, aviso.destinatario_id)
    return aviso


def _laco(Sessao: sessionmaker, parar: threading.Event) -> None:
    cliente = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=10)
    while not parar.is_set():
        try:
            item = cliente.brpop([FILA], timeout=5)
            if item:
                gravar(Sessao, item[1])
        except redis.RedisError as erro:
            log.warning("Fila indisponível (%s). Tentando de novo em 3 s.", erro)
            time.sleep(3)
        except Exception:  # nunca deixa a thread morrer por um evento ruim
            log.exception("Erro ao processar evento")


def iniciar(Sessao: sessionmaker) -> threading.Event:
    parar = threading.Event()
    threading.Thread(target=_laco, args=(Sessao, parar), name="consumidor", daemon=True).start()
    return parar
