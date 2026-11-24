from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Chamado(Base):
    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text)
    prioridade: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="aberto")
    # Sem chave estrangeira: usuários e ativos moram em outros serviços (outros bancos).
    # Guardamos só o id; a existência é conferida por HTTP na hora de gravar.
    solicitante_id: Mapped[int] = mapped_column(index=True)
    tecnico_id: Mapped[int | None] = mapped_column(nullable=True)
    ativo_id: Mapped[int | None] = mapped_column(nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime)
    prazo_sla: Mapped[datetime] = mapped_column(DateTime)

    comentarios: Mapped[list["Comentario"]] = relationship(
        back_populates="chamado", order_by="Comentario.id", cascade="all, delete-orphan", lazy="selectin"
    )


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Esta chave estrangeira continua: as duas tabelas são do mesmo serviço
    chamado_id: Mapped[int] = mapped_column(ForeignKey("chamados.id"))
    autor_id: Mapped[int]  # id de um usuário do serviço de Usuários (sem chave estrangeira)
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    chamado: Mapped[Chamado] = relationship(back_populates="comentarios")
