"""Banco do serviço de Notificações. Nenhum outro serviço acessa este banco."""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from comum.config import url_do_banco
from comum.servico_base import conectar

engine, SessionLocal = conectar(url_do_banco("sqlite:///./notificacoes.db"))


class Base(DeclarativeBase):
    pass


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40))
    destinatario_id: Mapped[int] = mapped_column(index=True)
    mensagem: Mapped[str] = mapped_column(String(300))
    criada_em: Mapped[datetime] = mapped_column(DateTime)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
