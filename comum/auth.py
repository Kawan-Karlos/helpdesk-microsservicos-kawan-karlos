"""Dependências do FastAPI para exigir login e perfil em qualquer serviço.

Cada serviço confere o token sozinho (assinatura, emissor e validade), sem
perguntar ao serviço de Usuários a cada requisição.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from comum import tokens

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class UsuarioLogado:
    id: int
    perfil: str
    token: str  # repassado quando este serviço chama outro

    @property
    def cabecalho(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> UsuarioLogado:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    try:
        usuario_id, perfil = tokens.ler(credenciais.credentials)
    except tokens.TokenInvalido:
        raise NAO_AUTENTICADO
    return UsuarioLogado(id=usuario_id, perfil=perfil, token=credenciais.credentials)


def exigir_perfil(*perfis: str):
    """Libera a rota só para os perfis informados."""
    def verificar(usuario: UsuarioLogado = Depends(usuario_atual)) -> UsuarioLogado:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar
