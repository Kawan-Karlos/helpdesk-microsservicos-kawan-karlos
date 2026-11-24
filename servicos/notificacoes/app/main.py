"""Serviço de Notificações: dono da tabela de notificações."""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import consumidor
from app.database import Base, Notificacao, SessionLocal, engine, get_db
from comum.auth import UsuarioLogado, usuario_atual
from comum.servico_base import criar_app


class NotificacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    destinatario_id: int
    mensagem: str
    criada_em: datetime


@asynccontextmanager
async def ciclo_de_vida(app):
    Base.metadata.create_all(engine)
    parar = consumidor.iniciar(SessionLocal) if os.getenv("CONSUMIR_FILA", "1") == "1" else None
    yield
    if parar:
        parar.set()


app = criar_app("notificacoes", ciclo_de_vida)


@app.get("/notificacoes", response_model=list[NotificacaoSaida], tags=["Notificações"])
def minhas_notificacoes(usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Cada usuário vê só as próprias notificações (as mais novas primeiro)."""
    consulta = select(Notificacao).where(Notificacao.destinatario_id == usuario.id).order_by(Notificacao.id.desc())
    return list(db.scalars(consulta))
