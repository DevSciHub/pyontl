"""Transporte HTTP compartilhado pelas consultas ao ONTL."""

import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import APIError, ResponseError

BASE_URL = "https://ontl-apim.infrasa.gov.br"
_session = requests.Session()
_session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]), raise_on_status=False,
)))


def validate_slug(slug):
    if not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9_\-]+", slug):
        raise ValueError("Informe um identificador de dataset válido do catálogo.")
    return slug


def make_request(url, params=None, timeout=60):
    """GET com timeout e novas tentativas para falhas transitórias.

    Lança APIError para HTTP/conexão e ResponseError para JSON inválido.
    Nunca transforma uma falha em resposta vazia.
    """
    try:
        response = _session.get(url, params=params, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        raise APIError("Falha de conexão com o ONTL: {}".format(exc), url=url) from exc
    if not response.ok:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = str(body.get("message") or body.get("error") or "")[:300]
        except ValueError:
            pass
        raise APIError(
            "ONTL retornou HTTP {}{}".format(
                response.status_code, ": " + detail if detail else "."),
            url=url, status_code=response.status_code,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ResponseError("O ONTL retornou uma resposta que não é JSON.", url=url) from exc
