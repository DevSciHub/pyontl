"""
pyontl - Biblioteca para acesso a dados da ONTL
"""

from .core import getDataset
from .catalog import buscar, catalogo
from .client import Dataset, consultar, dataset
from .exceptions import APIError, IncompleteDownloadError, ONTLError, ResponseError
from .metadata import getMetadados, getMetadados_filterableColumns

__version__ = "1.1.0"
__all__ = [
    "buscar", "catalogo", "dataset", "consultar", "Dataset",
    "ONTLError", "APIError", "ResponseError", "IncompleteDownloadError",
    "getDataset",
    "getMetadados", 
    "getMetadados_filterableColumns"
]
