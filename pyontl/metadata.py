import pandas as pd
from .utils import make_request

def getMetadados(dataset="antt_pracaspedagio"):
    """
    Obtém metadados completos e estruturais do dataset especificado.
    
    Fornece informações detalhadas sobre a estrutura, colunas, tipos de dados
    e metadados técnicos do conjunto de dados, essencial para entender
    a organização dos dados antes de realizar consultas.
    
    Args:
        dataset (str, optional): Nome do dataset da ONTL. 
            Padrão: "antt_pracaspedagio".
        
    Returns:
        dict: Dicionário com metadados completos incluindo:
            - table: Nome da tabela
            - filterableColumns: Lista de colunas filtráveis
            - Estrutura completa de metadados da API
        
    Examples:
        >>> metadados = getMetadados()
        >>> print(f"Colunas filtráveis: {metadados.get('filterableColumns', [])}")
        >>> print(f"Estrutura da tabela: {metadados.get('table', 'N/A')}")
        
    Raises:
        Exception: Em caso de erro na requisição HTTP.
    """
    
    metadados_url = f"https://ontl-apim.infrasa.gov.br/api/public/datasets/{dataset}/meta"
    
    try:
        return make_request(metadados_url)
    except Exception as e:
        print(f"Erro ao buscar metadados: {e}")
        return {}

def getMetadados_filterableColumns(dataset="antt_pracaspedagio"):
    """
    Recupera lista de colunas filtráveis dos metadados do dataset.
    
    Gera um DataFrame com as colunas que podem ser utilizadas para filtrar
    os dados na API, facilitando a construção de consultas específicas.
    
    Args:
        dataset (str, optional): Nome do dataset da ONTL.
            Padrão: "antt_pracaspedagio".
            
    Returns:
        pandas.DataFrame: DataFrame com duas colunas:
            - dataset: Nome do dataset
            - column_name: Nome da coluna filtrável
        
    Examples:
        >>> colunas = getMetadados_filterableColumns()
        >>> print(f"Número de colunas filtráveis: {len(colunas)}")
        >>> print(colunas.head())
        
    Raises:
        Exception: Em caso de erro ao acessar os metadados.
    """

    try:
        meta = getMetadados(dataset)
        cols = meta.get("filterableColumns ", [])
        table = meta.get("table", [])
        
        return pd.DataFrame({
            "dataset": [table] * len(cols),
            "column_name": cols
        })
        
    except Exception as e:
        print(f"Erro ao recuperar metadados de colunas filtráveis: {e}")
        return pd.DataFrame({"dataset": [], "column_name": []})
