"""
pyontl - Biblioteca para acesso a dados da ONTL
"""

from .core import getDataset
from .metadata import getMetadados, getMetadados_filterableColumns

__version__ = "1.0.2"
__all__ = [
    "getDataset",
    "getMetadados", 
    "getMetadados_filterableColumns"
]