"""Descoberta de datasets diretamente da árvore publicada pelo ONTL."""

from functools import lru_cache
import re
import time
import unicodedata

import pandas as pd

from .exceptions import ResponseError
from .utils import BASE_URL, make_request

CATALOG_COLUMNS = ["id", "dataset", "nome", "descricao", "tema", "caminho",
                   "url", "consultavel"]
_CACHE_SECONDS = 3600


def _normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value))
                   if not unicodedata.combining(c)).casefold()


@lru_cache(maxsize=1)
def _fetch_catalog(bucket):
    url = BASE_URL + "/api/gerencial/tree"
    tree = make_request(url)
    if not isinstance(tree, list):
        raise ResponseError("Catálogo inválido: a árvore deve ser uma lista.", url=url)
    records = []

    def walk(nodes, path):
        for node in nodes:
            if not isinstance(node, dict):
                raise ResponseError("Catálogo inválido: nó inválido.", url=url)
            name = node.get("name") or ""
            if not isinstance(name, str):
                raise ResponseError("Catálogo inválido: nome inválido.", url=url)
            if node.get("type") == "dataset":
                detail = node.get("dataset") or {}
                if not isinstance(detail, dict):
                    raise ResponseError("Catálogo inválido: descrição inválida.", url=url)
                if detail.get("visibility", "public") != "public":
                    continue
                slug = node.get("slug") or detail.get("api_link") or ""
                slug = str(slug).rstrip("/").rsplit("/", 1)[-1]
                valid = bool(re.fullmatch(r"[A-Za-z0-9_\-]+", slug))
                records.append({
                    "id": node.get("id"), "dataset": slug if valid else None,
                    "nome": name, "descricao": detail.get("description") or "",
                    "tema": path[0] if path else "",
                    "caminho": " > ".join(path + [name]),
                    "url": BASE_URL + "/api/public/datasets/" + slug if valid else None,
                    "consultavel": valid,
                })
            children = node.get("children", [])
            if not isinstance(children, list):
                raise ResponseError("Catálogo inválido: filhos devem ser uma lista.", url=url)
            walk(children, path + [name])

    walk(tree, [])
    return records


def catalogo(atualizar=False):
    """Lista o catálogo online, sem planilha local.

    Cache em memória por até uma hora. atualizar=True força nova leitura.
    consultavel indica presença de identificador, não disponibilidade da API.
    """
    if atualizar:
        _fetch_catalog.cache_clear()
    records = _fetch_catalog(int(time.monotonic() // _CACHE_SECONDS))
    return pd.DataFrame(records, columns=CATALOG_COLUMNS).copy(deep=True)


def buscar(texto="", tema=None, atualizar=False):
    """Busca todas as palavras no catálogo, ignorando acentos e caixa.

    tema restringe por correspondência parcial no tema raiz.
    """
    if not isinstance(texto, str) or (tema is not None and not isinstance(tema, str)):
        raise ValueError("texto e tema devem ser strings.")
    frame = catalogo(atualizar=atualizar)
    if frame.empty:
        return frame
    terms = _normalize(texto).split()
    searchable = frame[["nome", "descricao", "dataset", "caminho"]].fillna("").agg(" ".join, axis=1)
    mask = searchable.map(lambda value: all(term in _normalize(value) for term in terms))
    if tema is not None:
        mask &= frame["tema"].map(lambda value: _normalize(tema) in _normalize(value))
    return frame.loc[mask.astype(bool)].reset_index(drop=True)
