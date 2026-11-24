"""Chamadas HTTP para os serviços de Usuários e Inventário.

No monólito eram chamadas de função. Agora passam pela rede, então:
- toda chamada tem tempo limite (TIMEOUT_SEGUNDOS);
- o token do usuário é repassado no cabeçalho Authorization;
- se o outro serviço estiver fora do ar ou demorar, levantamos
  ServicoIndisponivel, que vira uma resposta 503 com uma mensagem clara.
"""
import logging
import os

import httpx

from comum.auth import UsuarioLogado
from comum.erros import NaoEncontrado, RegraDeNegocio, ServicoIndisponivel

log = logging.getLogger("helpdesk.chamados")

USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000")
TIMEOUT_SEGUNDOS = float(os.getenv("TIMEOUT_SEGUNDOS", "3"))

# Nos testes, trocamos por um httpx.MockTransport para simular os outros serviços
transporte: httpx.BaseTransport | None = None


def _buscar(nome: str, url: str, quem: UsuarioLogado, nao_encontrado: str) -> dict:
    try:
        with httpx.Client(timeout=TIMEOUT_SEGUNDOS, transport=transporte) as cliente:
            resposta = cliente.get(url, headers=quem.cabecalho)
    except httpx.TimeoutException:
        log.warning("Tempo esgotado ao chamar %s (%s)", nome, url)
        raise ServicoIndisponivel(f"O serviço de {nome} demorou demais para responder. Tente de novo em instantes.")
    except httpx.HTTPError as erro:
        log.warning("Falha ao chamar %s (%s): %s", nome, url, erro)
        raise ServicoIndisponivel(f"O serviço de {nome} está indisponível no momento. Tente de novo em instantes.")

    if resposta.status_code == 404:
        raise NaoEncontrado(nao_encontrado)
    if resposta.status_code != 200:
        log.warning("%s respondeu %s para %s", nome, resposta.status_code, url)
        raise ServicoIndisponivel(f"O serviço de {nome} respondeu com erro ({resposta.status_code}).")
    return resposta.json()


def obter_ativo(ativo_id: int, quem: UsuarioLogado) -> dict:
    """Antes: inventario.obter(db, ativo_id). Agora: GET /ativos/{id} no serviço de Inventário."""
    return _buscar("inventário", f"{INVENTARIO_URL}/ativos/{ativo_id}", quem, f"Ativo {ativo_id} não encontrado.")


def obter_tecnico(usuario_id: int, quem: UsuarioLogado) -> dict:
    """Antes: usuarios.obter_tecnico(db, id). Agora: GET /usuarios/{id} no serviço de Usuários."""
    usuario = _buscar("usuários", f"{USUARIOS_URL}/usuarios/{usuario_id}", quem, f"Usuário {usuario_id} não encontrado.")
    if usuario.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
    return usuario
