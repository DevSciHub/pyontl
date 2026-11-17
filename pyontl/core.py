"""Compatibilidade com a interface original da pyontl."""

from .client import consultar


def getDataset(year=2000, dataset="antt_pracaspedagio",
               column_order_by="int_idapracaspedagio", column_filter_year="int_ano"):
    """Consulta por ano com validação e erros explícitos.

    Mantém nomes e padrões anteriores. Para outros datasets, informe as colunas
    correspondentes ou use consultar() com filtros gerais. Falhas agora lançam
    ONTLError em vez de retornar dados vazios ou parciais silenciosamente.
    """
    return consultar(dataset, filtros={column_filter_year: year},
                     order_by=column_order_by, order_dir="desc")
