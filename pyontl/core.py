import pandas as pd
from .utils import make_request

def getDataset(year=2000, dataset="antt_pracaspedagio", 
               column_order_by="int_idapracaspedagio", 
               column_filter_year="int_ano"):
    """
    Busca dados paginados de um dataset específico por ano.
    
    Esta função realiza requisições paginadas à API da ONTL para recuperar
    todos os registros de um determinado ano.
    
    Args:
        year (int, optional): Ano dos dados a serem buscados. Padrão: 2000.
        dataset (str, optional): Nome do dataset. Padrão: "antt_pracaspedagio".
        column_order_by (str, optional): Coluna para ordenação dos resultados.
            Padrão: "int_idapracaspedagio".
        column_filter_year (str, optional): Nome da coluna que contém o ano
            para filtragem. Padrão: "int_ano".
    
    Returns:
        pandas.DataFrame: DataFrame contendo todos os registros encontrados
        para o ano especificado.
    
    Raises:
        Exception: Em caso de erro na requisição HTTP.
    
    Examples:
        >>> import pyontl
        >>> # Buscar dados de 2023
        >>> df_2023 = pyontl.getDataset(year=2023)
        >>> print(f"Encontrados {len(df_2023)} registros")
        Encontrados 1500 registros
        
        >>> # Buscar dados de dataset específico
        >>> df_custom = pyontl.getDataset(
        ...     year=2022,
        ...     dataset="meu_dataset",
        ...     column_filter_year="ano"
        ... )
    
    Note:
        A função realiza múltiplas requisições paginadas até recuperar
        todos os dados disponíveis.
    """
    
    base_url = f"https://ontl-apim.infrasa.gov.br/api/public/datasets/{dataset}"
    all_records = []
    page = 1
    per_page = 100
    
    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "order_by": column_order_by,
            column_filter_year: year
        }
        
        try:
            response = make_request(base_url, params=params)
            data = response.get("data", [])
            
            if not data:
                break
                
            all_records.extend(data)
            page += 1
            
        except Exception as e:
            print(f"Erro ao buscar dados para o ano {year}: {e}")
            break
    
    return pd.DataFrame(all_records)