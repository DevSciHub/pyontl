"""Consulta validada e paginação de datasets."""

from collections.abc import Mapping
from datetime import date, datetime, timezone
from functools import cached_property
import hashlib
import json

import pandas as pd

from .catalog import catalogo
from .exceptions import IncompleteDownloadError, ResponseError
from .metadata import filterable_columns, getMetadados
from .utils import BASE_URL, make_request, validate_slug

_RESERVED = {"page", "per_page", "order_by", "order_dir"}


class Dataset:
    """Dataset ONTL com metadados carregados sob demanda por instância."""

    def __init__(self, identificador):
        self.identificador = validate_slug(identificador)
        self.url = BASE_URL + "/api/public/datasets/" + self.identificador

    @cached_property
    def metadados(self):
        return getMetadados(self.identificador)

    @property
    def descricao(self):
        frame = catalogo()
        matches = frame.loc[frame["dataset"] == self.identificador, "descricao"]
        return matches.iloc[0] if not matches.empty else ""

    @property
    def colunas(self):
        """DataFrame com nome, tipo e indicação de filtro permitido."""
        meta = self.metadados
        filters = set(filterable_columns(meta))
        return pd.DataFrame([
            {"nome": name, "tipo": meta.get("types", {}).get(name),
             "filtravel": name in filters}
            for name in meta["columns"]
        ], columns=["nome", "tipo", "filtravel"])

    def consultar(self, filtros=None, order_by=None, order_dir="asc", per_page=100):
        """Baixa todas as páginas ou lança erro, sem retornar dados parciais.

        Os filtros usam os nomes reais das colunas e igualdade conforme a API.
        Nenhum filtro anual é presumido. A API pode exigir pelo menos um filtro.
        Prefira uma coluna única para order_by quando disponível.
        """
        if isinstance(per_page, bool) or not isinstance(per_page, int) or not 1 <= per_page <= 1000:
            raise ValueError("per_page deve ser um inteiro entre 1 e 1000.")
        if order_dir not in ("asc", "desc"):
            raise ValueError("order_dir deve ser 'asc' ou 'desc'.")
        if filtros is None:
            filtros = {}
        if not isinstance(filtros, Mapping):
            raise ValueError("filtros deve ser um mapeamento de coluna para valor.")
        meta = self.metadados
        columns = meta["columns"]
        allowed = set(filterable_columns(meta)) - _RESERVED
        invalid = [key for key in filtros if key not in allowed]
        if invalid:
            raise ValueError("Filtros inválidos: {}. Consulte dataset.colunas.".format(
                ", ".join(map(str, invalid))))
        if not columns:
            raise ResponseError("O dataset não informa colunas para consulta.", url=self.url)
        if order_by is None:
            order_by = next((c for c in columns if c.startswith("int_ida")), columns[0])
        if order_by not in columns:
            raise ValueError("Coluna de ordenação inválida: {}.".format(order_by))
        filters = {}
        for key, value in filtros.items():
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            if value is None or not isinstance(value, (str, int, float, bool)) or (
                    isinstance(value, float) and not float("-inf") < value < float("inf")):
                raise ValueError("O filtro {} deve ter valor escalar não nulo e finito.".format(key))
            filters[key] = value

        records, seen = [], set()
        expected = None
        page = 1
        while True:
            params = dict(filters, page=page, per_page=per_page,
                          order_by=order_by, order_dir=order_dir)
            response = make_request(self.url, params=params)
            if (not isinstance(response, dict) or not isinstance(response.get("data"), list)
                    or not all(isinstance(row, dict) for row in response["data"])):
                raise ResponseError("Página {} inválida: lista de registros ausente ou inválida.".format(page), url=self.url)
            page_meta = response.get("meta", {})
            if not isinstance(page_meta, dict):
                raise ResponseError("Metadados de paginação inválidos.", url=self.url)
            total = page_meta.get("total")
            if total is not None:
                if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                    raise ResponseError("Total de registros inválido.", url=self.url)
                if expected is not None and total != expected:
                    raise IncompleteDownloadError("O total mudou durante a consulta; execute novamente.")
                expected = total
            data = response["data"]
            if not data:
                if expected is not None and len(records) != expected:
                    raise IncompleteDownloadError("Paginação encerrada com {} de {} registros.".format(len(records), expected))
                break
            fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).digest()
            if fingerprint in seen:
                raise IncompleteDownloadError("A API repetiu uma página; a consulta foi interrompida.")
            seen.add(fingerprint)
            records.extend(data)
            if expected is not None:
                if len(records) > expected:
                    raise IncompleteDownloadError("A API retornou mais registros que o total declarado.")
                if len(records) == expected:
                    break
            page += 1

        frame = pd.DataFrame(records) if records else pd.DataFrame(columns=columns)
        frame.attrs.update({
            "dataset": self.identificador, "url": self.url, "filtros": filters,
            "consultado_em": datetime.now(timezone.utc).isoformat(),
            "order_by": order_by, "order_dir": order_dir, "total": len(records),
        })
        return frame


def dataset(identificador):
    """Cria um Dataset sem executar requisições imediatamente."""
    return Dataset(identificador)


def consultar(identificador, filtros=None, order_by=None, order_dir="asc", per_page=100):
    """Atalho para Dataset(identificador).consultar(...)."""
    return Dataset(identificador).consultar(filtros, order_by, order_dir, per_page)
