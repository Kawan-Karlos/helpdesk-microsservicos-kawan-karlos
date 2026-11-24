"""Serviço de Inventário: dono da tabela de ativos."""
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import servico
from app.database import Base, SessionLocal, engine, get_db
from app.esquemas import AtivoCriar, AtivoSaida
from comum.auth import exigir_perfil, usuario_atual
from comum.servico_base import criar_app

# Ids 1 a 3, usados pelos dados de exemplo do serviço de Chamados
EXEMPLOS = [
    AtivoCriar(patrimonio="PAT-0001", tipo="computador", descricao="Desktop Dell OptiPlex", setor="Financeiro"),
    AtivoCriar(patrimonio="PAT-0002", tipo="impressora", descricao="Impressora HP LaserJet", setor="RH"),
    AtivoCriar(patrimonio="PAT-0003", tipo="notebook", descricao="Notebook Lenovo ThinkPad", setor="TI"),
]


@asynccontextmanager
async def ciclo_de_vida(app):
    Base.metadata.create_all(engine)
    if os.getenv("DADOS_EXEMPLO", "1") == "1":
        with SessionLocal() as db:
            if not servico.listar(db):
                for ativo in EXEMPLOS:
                    servico.criar(db, ativo)
    yield


router = APIRouter(prefix="/ativos", tags=["Inventário"])


@router.post("", response_model=AtivoSaida, status_code=201, dependencies=[Depends(exigir_perfil("tecnico", "admin"))])
def criar_ativo(dados: AtivoCriar, db: Session = Depends(get_db)):
    return servico.criar(db, dados)


@router.get("", response_model=list[AtivoSaida], dependencies=[Depends(usuario_atual)])
def listar_ativos(setor: str | None = Query(None, max_length=80), db: Session = Depends(get_db)):
    return servico.listar(db, setor)


@router.get("/{ativo_id}", response_model=AtivoSaida, dependencies=[Depends(usuario_atual)])
def obter_ativo(ativo_id: int, db: Session = Depends(get_db)):
    """Usado pelo serviço de Chamados para conferir o equipamento."""
    return servico.obter(db, ativo_id)


app = criar_app("inventario", ciclo_de_vida)
app.include_router(router)
