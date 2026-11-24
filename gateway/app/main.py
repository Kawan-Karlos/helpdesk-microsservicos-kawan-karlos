"""API Gateway do HelpDesk.

- Serve a tela (index.html, app.js, estilo.css) no mesmo endereço de antes.
- Encaminha cada rota para o serviço dono dela, repassando o token.
- Se um serviço estiver fora do ar, responde 503 só para as rotas dele:
  o resto do sistema continua funcionando.
- GET /saude mostra quais serviços estão no ar.

O gateway não confere o token: quem confere é cada serviço. Assim, mesmo que
alguém chegasse a um serviço sem passar pelo gateway, ainda precisaria de um
token válido.
"""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from comum.seguranca_http import CabecalhosDeSeguranca

WEB = Path(os.getenv("WEB_DIR", Path(__file__).parent.parent / "web"))
TIMEOUT_SEGUNDOS = float(os.getenv("TIMEOUT_SEGUNDOS", "10"))

SERVICOS = {
    "usuarios": os.getenv("USUARIOS_URL", "http://usuarios:8000"),
    "inventario": os.getenv("INVENTARIO_URL", "http://inventario:8000"),
    "chamados": os.getenv("CHAMADOS_URL", "http://chamados:8000"),
    "notificacoes": os.getenv("NOTIFICACOES_URL", "http://notificacoes:8000"),
}

# Primeiro pedaço do caminho -> serviço dono da rota
ROTAS = {
    "auth": "usuarios",
    "usuarios": "usuarios",
    "ativos": "inventario",
    "chamados": "chamados",
    "notificacoes": "notificacoes",
}

NOMES = {"usuarios": "usuários", "inventario": "inventário", "chamados": "chamados", "notificacoes": "notificações"}

# Só estes cabeçalhos seguem para os serviços (nada de cookies ou cabeçalhos internos forjados)
REPASSAR = ("authorization", "content-type", "accept")
DEVOLVER = ("content-type", "www-authenticate", "retry-after")

# Nos testes, trocamos por um httpx.MockTransport
transporte: httpx.AsyncBaseTransport | None = None


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS, transport=transporte, follow_redirects=False)
    yield
    await app.state.http.aclose()


app = FastAPI(title="HelpDesk TI · gateway", lifespan=ciclo_de_vida, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CabecalhosDeSeguranca)


@app.get("/", include_in_schema=False)
def tela_inicial():
    return FileResponse(WEB / "index.html")


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/estilo.css", include_in_schema=False)
def estilo():
    return FileResponse(WEB / "estilo.css", media_type="text/css")


@app.get("/saude")
async def saude(request: Request):
    """Pergunta o /saude de cada serviço ao mesmo tempo."""
    async def checar(nome: str, url: str) -> tuple[str, str]:
        try:
            r = await request.app.state.http.get(f"{url}/saude", timeout=2)
            return nome, "no ar" if r.status_code == 200 else f"erro {r.status_code}"
        except httpx.HTTPError:
            return nome, "fora do ar"

    resultado = dict(await asyncio.gather(*(checar(n, u) for n, u in SERVICOS.items())))
    tudo_ok = all(v == "no ar" for v in resultado.values())
    return JSONResponse(status_code=200 if tudo_ok else 503,
                        content={"status": "ok" if tudo_ok else "degradado", "servicos": resultado})


@app.api_route("/{caminho:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def encaminhar(caminho: str, request: Request):
    servico = ROTAS.get(caminho.split("/", 1)[0])
    if servico is None:
        return JSONResponse(status_code=404, content={"detail": "Rota não encontrada."})

    cabecalhos = {k: v for k, v in request.headers.items() if k.lower() in REPASSAR}
    # O IP de quem acessou (usado pelo limite de tentativas de login).
    # Substitui qualquer X-Forwarded-For enviado pelo cliente, para não ser forjado.
    cabecalhos["x-forwarded-for"] = request.client.host if request.client else "-"
    try:
        resposta = await request.app.state.http.request(
            request.method, f"{SERVICOS[servico]}/{caminho}", params=request.query_params,
            content=await request.body(), headers=cabecalhos,
        )
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"detail": f"O serviço de {NOMES[servico]} demorou demais para responder."})
    except httpx.HTTPError:
        return JSONResponse(status_code=503, content={"detail": f"O serviço de {NOMES[servico]} está fora do ar. Tente de novo em instantes."})

    return Response(content=resposta.content, status_code=resposta.status_code,
                    headers={k: v for k, v in resposta.headers.items() if k.lower() in DEVOLVER})
