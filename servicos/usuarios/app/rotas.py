from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import limite, senhas, servico
from app.database import get_db
from app.esquemas import Login, Perfil, TokenSaida, UsuarioCriar, UsuarioPublico, UsuarioSaida
from comum import tokens
from comum.auth import NAO_AUTENTICADO, UsuarioLogado, exigir_perfil, usuario_atual

auth = APIRouter(prefix="/auth", tags=["Autenticação"])
usuarios = APIRouter(prefix="/usuarios", tags=["Usuários"])


@auth.post("/login", response_model=TokenSaida)
def login(dados: Login, request: Request, db: Session = Depends(get_db)):
    email = dados.email.lower()
    # Atrás do gateway, o IP real chega pelo X-Forwarded-For (uvicorn --proxy-headers)
    chave = f"{email}|{request.client.host if request.client else '-'}"
    if limite.bloqueado(chave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Tente de novo em alguns minutos.")

    usuario = servico.buscar_por_email(db, email)
    # Confere a senha mesmo sem usuário, para o tempo de resposta não revelar se o e-mail existe
    senha_ok = senhas.conferir(dados.senha, usuario.senha_hash if usuario else senhas.HASH_FALSO)
    if not usuario or not senha_ok or not usuario.ativo:
        limite.registrar_falha(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")

    limite.limpar(chave)
    token, expira = tokens.criar(usuario.id, usuario.perfil)
    return TokenSaida(access_token=token, expira_em=expira, usuario=UsuarioSaida.model_validate(usuario))


@auth.get("/eu", response_model=UsuarioSaida)
def quem_sou_eu(logado: UsuarioLogado = Depends(usuario_atual), db: Session = Depends(get_db)):
    # Aqui o banco de usuários está à mão: confere se a conta ainda existe e está ativa
    usuario = db.get(servico.Usuario, logado.id)
    if usuario is None or not usuario.ativo:
        raise NAO_AUTENTICADO
    return usuario


@usuarios.post("", response_model=UsuarioSaida, status_code=201, dependencies=[Depends(exigir_perfil("admin"))])
def criar_usuario(dados: UsuarioCriar, db: Session = Depends(get_db)):
    return servico.criar(db, dados)


@usuarios.get("", response_model=list[UsuarioPublico], dependencies=[Depends(usuario_atual)])
def listar_usuarios(perfil: Perfil | None = None, db: Session = Depends(get_db)):
    return servico.listar(db, perfil)


@usuarios.get("/{usuario_id}", response_model=UsuarioPublico, dependencies=[Depends(usuario_atual)])
def obter_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Usado pelo serviço de Chamados para conferir o técnico."""
    return servico.obter(db, usuario_id)
