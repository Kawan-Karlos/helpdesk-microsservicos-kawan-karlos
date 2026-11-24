"""Configurações comuns, lidas das variáveis de ambiente."""
import logging
import os
import secrets
from pathlib import Path

log = logging.getLogger("helpdesk")


def ler_segredo(nome: str) -> str:
    """Lê um segredo da variável NOME ou do arquivo indicado em NOME_ARQUIVO.

    No Docker Compose, o contêiner `segredos` gera os arquivos na primeira
    subida. Assim nenhum segredo fica no código e ninguém precisa criá-lo à mão.
    Se o .env definir a variável, ela tem prioridade.
    """
    valor = os.getenv(nome, "")
    arquivo = os.getenv(f"{nome}_ARQUIVO")
    if not valor and arquivo and Path(arquivo).is_file():
        valor = Path(arquivo).read_text().strip()
    return valor


JWT_SEGREDO = ler_segredo("JWT_SEGREDO")
if len(JWT_SEGREDO) < 32:
    # Sem um segredo compartilhado, os serviços não aceitariam os tokens uns dos outros.
    log.warning("JWT_SEGREDO ausente ou curto; usando um segredo aleatório (só serve para testes).")
    JWT_SEGREDO = secrets.token_urlsafe(48)

JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))

# Tamanho máximo do corpo de uma requisição (em bytes)
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024

DOCS_ATIVA = os.getenv("DOCS", "1") == "1"


def url_do_banco(padrao: str) -> str:
    """DATABASE_URL pode conter {senha}, que é trocada pelo segredo DB_SENHA."""
    url = os.getenv("DATABASE_URL", padrao)
    return url.replace("{senha}", ler_segredo("DB_SENHA")) if "{senha}" in url else url
