"""Estrutura e filtros dos datasets."""

import pandas as pd

from .exceptions import ResponseError
from .utils import BASE_URL, make_request, validate_slug


def getMetadados(dataset="antt_pracaspedagio"):
    """Retorna metadados. Falhas são propagadas como ONTLError."""
    url = "{}/api/public/datasets/{}/meta".format(BASE_URL, validate_slug(dataset))
    meta = make_request(url)
    if (not isinstance(meta, dict) or not isinstance(meta.get("columns"), list)
            or not all(isinstance(c, str) for c in meta["columns"])):
        raise ResponseError("Metadados inválidos: lista de colunas ausente ou inválida.", url=url)
    for key in ("filterable_columns", "filterableColumns"):
        if key in meta and (not isinstance(meta[key], list)
                            or not all(isinstance(c, str) for c in meta[key])):
            raise ResponseError("Metadados inválidos: lista de filtros inválida.", url=url)
    if not isinstance(meta.get("types", {}), dict):
        raise ResponseError("Metadados inválidos: tipos de colunas inválidos.", url=url)
    return meta


def filterable_columns(meta):
    """Aceita as duas grafias da API, preservando uma lista vazia."""
    return meta.get("filterable_columns", meta.get("filterableColumns", []))


def getMetadados_filterableColumns(dataset="antt_pracaspedagio"):
    """Retorna as colunas filtráveis, nas colunas dataset e column_name."""
    meta = getMetadados(dataset)
    cols = filterable_columns(meta)
    return pd.DataFrame({"dataset": [meta.get("table", dataset)] * len(cols),
                         "column_name": cols})
