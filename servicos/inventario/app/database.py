"""Banco do serviço de Inventário. Nenhum outro serviço acessa este banco."""
from sqlalchemy.orm import DeclarativeBase

from comum.config import url_do_banco
from comum.servico_base import conectar

engine, SessionLocal = conectar(url_do_banco("sqlite:///./inventario.db"))


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
