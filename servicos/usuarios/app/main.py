"""Serviço de Usuários: dono da tabela de usuários e do login."""
import os
from contextlib import asynccontextmanager

from app.database import Base, SessionLocal, engine
from app.esquemas import UsuarioCriar
from app.rotas import auth, usuarios
from app import servico
from comum.servico_base import criar_app

SENHA_EXEMPLO = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")

# A ordem importa: os ids (1 a 5) são usados pelos dados de exemplo dos outros serviços
EXEMPLOS = [
    ("Admin TI", "admin@empresa.com", "admin"),
    ("Ana Souza", "ana@empresa.com", "solicitante"),
    ("Bruno Lima", "bruno@empresa.com", "solicitante"),
    ("Carla Dias", "carla@empresa.com", "tecnico"),
    ("Diego Rocha", "diego@empresa.com", "tecnico"),
]


@asynccontextmanager
async def ciclo_de_vida(app):
    Base.metadata.create_all(engine)
    if os.getenv("DADOS_EXEMPLO", "1") == "1":
        with SessionLocal() as db:
            if not servico.listar(db):
                for nome, email, perfil in EXEMPLOS:
                    servico.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA_EXEMPLO))
    yield


app = criar_app("usuarios", ciclo_de_vida)
app.include_router(auth)
app.include_router(usuarios)
