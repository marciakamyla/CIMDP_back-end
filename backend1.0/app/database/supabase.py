
import logging
import os

import requests
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TIMEOUT_SEGUNDOS = 10


def obter_configuracao():
    """Verifica se as configurações do Supabase existem."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=500,
            detail="As configurações do Supabase não foram definidas.",
        )

    return SUPABASE_URL.rstrip("/"), SUPABASE_KEY


def fazer_requisicao(url):
    """Executa uma consulta ao Supabase com tratamento de erros."""
    _, chave = obter_configuracao()

    headers = {
        "apikey": chave,
        "Authorization": f"Bearer {chave}",
    }

    try:
        resposta = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()

        try:
            return resposta.json()
        except ValueError as erro:
            raise HTTPException(
                status_code=502,
                detail="O Supabase retornou uma resposta inválida.",
            ) from erro

    except requests.Timeout as erro:
        raise HTTPException(
            status_code=503,
            detail="O Supabase demorou para responder. Tente novamente.",
        ) from erro

    except requests.ConnectionError as erro:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao Supabase.",
        ) from erro

    except requests.HTTPError as erro:
        logger.error(
            "Erro HTTP do Supabase: status=%s",
            resposta.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail="O Supabase retornou um erro durante a consulta.",
        ) from erro

    except requests.RequestException as erro:
        logger.error(
            "Erro de comunicação com o Supabase: %s",
            type(erro).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Ocorreu um erro na comunicação com o Supabase.",
        ) from erro


def consultar_produtos():
    """Retorna todos os produtos cadastrados."""
    base_url, _ = obter_configuracao()
    url = f"{base_url}/rest/v1/produto?select=*"

    produtos = fazer_requisicao(url)

    if not isinstance(produtos, list):
        raise HTTPException(
            status_code=502,
            detail="O Supabase retornou produtos em formato inesperado.",
        )

    return produtos


def consultar_produto_por_id(id_produto):
    """Retorna um produto pelo ID ou None se não existir."""
    if isinstance(id_produto, bool) or not isinstance(id_produto, int) or id_produto <= 0:
        raise HTTPException(
            status_code=400,
            detail="O ID do produto deve ser um inteiro positivo.",
        )

    base_url, _ = obter_configuracao()
    url = (
        f"{base_url}/rest/v1/produto"
        f"?id_produto=eq.{id_produto}&select=*"
    )

    produtos = fazer_requisicao(url)

    if not isinstance(produtos, list):
        raise HTTPException(
            status_code=502,
            detail="O Supabase retornou dados em formato inesperado.",
        )

    if not produtos:
        return None

    if not isinstance(produtos[0], dict):
        raise HTTPException(
            status_code=502,
            detail="O cadastro do produto possui formato inválido.",
        )

    return produtos[0]


def consultar_regras_por_produto(id_produto):
    """Retorna as regras ativas cadastradas para um produto."""
    if isinstance(id_produto, bool) or not isinstance(id_produto, int) or id_produto <= 0:
        raise HTTPException(
            status_code=400,
            detail="O ID do produto deve ser um inteiro positivo.",
        )

    base_url, _ = obter_configuracao()
    url = (
        f"{base_url}/rest/v1/regra_produto"
        f"?id_produto=eq.{id_produto}"
        "&ativo=eq.true"
        "&select=*"
        "&order=id_regra.asc"
    )

    regras = fazer_requisicao(url)

    if not isinstance(regras, list):
        raise HTTPException(
            status_code=502,
            detail="O Supabase retornou regras em formato inesperado.",
        )

    if not all(isinstance(regra, dict) for regra in regras):
        raise HTTPException(
            status_code=502,
            detail="Uma ou mais regras possuem formato inválido.",
        )

    return regras
