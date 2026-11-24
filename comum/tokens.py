"""Criação e validação dos tokens JWT (mesmo formato do monólito)."""
from datetime import datetime, timedelta, timezone

import jwt

from comum import config

PERFIS = ("solicitante", "tecnico", "admin")


class TokenInvalido(Exception):
    pass


def criar(usuario_id: int, perfil: str) -> tuple[str, datetime]:
    agora = datetime.now(timezone.utc)
    expira = agora + timedelta(minutes=config.TOKEN_MINUTOS)
    dados = {"sub": str(usuario_id), "perfil": perfil, "iat": agora, "exp": expira, "iss": config.JWT_EMISSOR}
    return jwt.encode(dados, config.JWT_SEGREDO, algorithm=config.JWT_ALGORITMO), expira


def ler(token: str) -> tuple[int, str]:
    """Devolve (id do usuário, perfil) do token, ou lança TokenInvalido."""
    try:
        dados = jwt.decode(
            token, config.JWT_SEGREDO, algorithms=[config.JWT_ALGORITMO], issuer=config.JWT_EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        if dados.get("perfil") not in PERFIS:
            raise TokenInvalido()
        return int(dados["sub"]), dados["perfil"]
    except (jwt.PyJWTError, ValueError) as erro:
        raise TokenInvalido() from erro
