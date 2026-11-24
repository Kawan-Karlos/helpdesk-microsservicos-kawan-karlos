"""Serviço de Chamados: dono das tabelas de chamados e comentários."""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import servico
from app.database import Base, SessionLocal, engine, get_db
from app.esquemas import (
    Atribuicao, ChamadoCriar, ChamadoSaida, ComentarioCriar, ComentarioSaida, MudancaStatus, Painel, Status,
)
from app.modelos import Chamado
from comum.auth import UsuarioLogado, usuario_atual
from comum.servico_base import criar_app


def carregar_exemplos(db: Session) -> None:
    """Mesmos chamados do monólito. Usa os ids fixos dos dados de exemplo dos outros
    serviços (Ana=2, Bruno=3, Carla=4; ativos 1 e 2), sem chamar a rede na subida."""
    if db.scalar(select(Chamado.id).limit(1)):
        return
    agora = datetime.now()
    for titulo, descricao, prioridade, ativo_id, solicitante_id, tecnico_id in [
        ("Computador não liga", "Apertei o botão e nada acontece.", "alta", 1, 2, 4),
        ("Impressora atolando papel", "Atola a cada 3 folhas.", "media", 2, 3, None),
        ("Acesso ao sistema de RH", "Preciso de acesso para a nova estagiária.", "baixa", None, 3, None),
    ]:
        db.add(Chamado(titulo=titulo, descricao=descricao, prioridade=prioridade, ativo_id=ativo_id,
                       solicitante_id=solicitante_id, tecnico_id=tecnico_id,
                       status="em_atendimento" if tecnico_id else "aberto",
                       criado_em=agora, prazo_sla=servico.calcular_prazo(prioridade, agora)))
    db.commit()


@asynccontextmanager
async def ciclo_de_vida(app):
    Base.metadata.create_all(engine)
    if os.getenv("DADOS_EXEMPLO", "1") == "1":
        with SessionLocal() as db:
            carregar_exemplos(db)
    yield


router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.post("", response_model=ChamadoSaida, status_code=201)
def abrir_chamado(dados: ChamadoCriar, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.abrir(db, dados, usuario)


@router.get("", response_model=list[ChamadoSaida])
def listar_chamados(status: Status | None = None, tecnico_id: int | None = None,
                    usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.listar(db, usuario, status, tecnico_id)


@router.get("/painel", response_model=Painel)
def painel(usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.painel(db, usuario)


@router.get("/{chamado_id}", response_model=ChamadoSaida)
def obter_chamado(chamado_id: int, usuario: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.obter(db, chamado_id, usuario)


@router.patch("/{chamado_id}/atribuir", response_model=ChamadoSaida)
def atribuir_chamado(chamado_id: int, dados: Atribuicao, usuario: UsuarioLogado = Depends(usuario_atual),
                     db: Session = Depends(get_db)):
    return servico.atribuir(db, chamado_id, dados.tecnico_id, usuario)


@router.patch("/{chamado_id}/status", response_model=ChamadoSaida)
def mudar_status(chamado_id: int, dados: MudancaStatus, usuario: UsuarioLogado = Depends(usuario_atual),
                 db: Session = Depends(get_db)):
    return servico.mudar_status(db, chamado_id, dados.status, usuario)


@router.post("/{chamado_id}/comentarios", response_model=ComentarioSaida, status_code=201)
def comentar(chamado_id: int, dados: ComentarioCriar, usuario: UsuarioLogado = Depends(usuario_atual),
             db: Session = Depends(get_db)):
    return servico.comentar(db, chamado_id, dados, usuario)


app = criar_app("chamados", ciclo_de_vida)
app.include_router(router)
