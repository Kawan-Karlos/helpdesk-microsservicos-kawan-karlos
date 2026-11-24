"""Erros de negócio e como eles viram respostas HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class NaoEncontrado(Exception):
    """O recurso pedido não existe (ou o usuário não pode vê-lo)."""


class RegraDeNegocio(Exception):
    """A operação viola uma regra do sistema."""


class SemPermissao(Exception):
    """O usuário está logado, mas não pode fazer esta operação."""


class ServicoIndisponivel(Exception):
    """Outro serviço necessário não respondeu a tempo."""


def registrar(app: FastAPI) -> None:
    for erro, codigo in ((NaoEncontrado, 404), (RegraDeNegocio, 422), (SemPermissao, 403), (ServicoIndisponivel, 503)):
        app.add_exception_handler(erro, lambda request, e, codigo=codigo: JSONResponse(status_code=codigo, content={"detail": str(e)}))

    @app.exception_handler(IntegrityError)
    def conflito(request: Request, erro: IntegrityError):
        # Não expõe detalhes do banco na resposta
        return JSONResponse(status_code=409, content={"detail": "O registro conflita com outro já existente."})
