"""Regras do serviço de Usuários."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import senhas
from app.esquemas import UsuarioCriar
from app.modelos import Usuario
from comum.erros import NaoEncontrado, RegraDeNegocio


def _salvar(db: Session, usuario: Usuario) -> Usuario:
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def criar(db: Session, dados: UsuarioCriar) -> Usuario:
    email = dados.email.lower()
    if buscar_por_email(db, email):
        raise RegraDeNegocio("Já existe um usuário com este e-mail.")
    return _salvar(db, Usuario(nome=dados.nome, email=email, perfil=dados.perfil,
                               senha_hash=senhas.gerar_hash(dados.senha)))


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.lower()))


def obter(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    return usuario


def listar(db: Session, perfil: str | None = None) -> list[Usuario]:
    consulta = select(Usuario).order_by(Usuario.id)
    if perfil:
        consulta = consulta.where(Usuario.perfil == perfil)
    return list(db.scalars(consulta))
