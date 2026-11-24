"""Regras do serviço de Inventário."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.esquemas import AtivoCriar
from app.modelos import Ativo
from comum.erros import NaoEncontrado, RegraDeNegocio


def criar(db: Session, dados: AtivoCriar) -> Ativo:
    if db.scalar(select(Ativo).where(Ativo.patrimonio == dados.patrimonio)):
        raise RegraDeNegocio("Já existe um ativo com este patrimônio.")
    ativo = Ativo(**dados.model_dump())
    db.add(ativo)
    db.commit()
    db.refresh(ativo)
    return ativo


def obter(db: Session, ativo_id: int) -> Ativo:
    ativo = db.get(Ativo, ativo_id)
    if ativo is None:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    return ativo


def listar(db: Session, setor: str | None = None) -> list[Ativo]:
    consulta = select(Ativo).order_by(Ativo.id)
    if setor:
        consulta = consulta.where(Ativo.setor == setor)
    return list(db.scalars(consulta))
