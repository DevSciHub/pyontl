import requests

def make_request(url, params=None, timeout=60):
    """
    Faz uma requisição HTTP GET com tratamento de erros.
    
    Função auxiliar para realizar requisições à API da ONTL com
    tratamento robusto de exceções e configurações de timeout.
    
    Args:
        url (str): URL para a requisição.
        params (dict, optional): Parâmetros de consulta (query string). 
            Padrão: None.
        timeout (int, optional): Timeout em segundos. Padrão: 60.
    
    Returns:
        dict: Resposta da API em formato JSON.
        
    Raises:
        Exception: Erro na requisição HTTP (conexão, timeout, etc.)
        
    Examples:
        >>> resposta = make_request("https://ontl-apim.infrasa.gov.br/api/public/datasets/antt_pracaspedagio/meta")
        >>> print(resposta.keys())
    """
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro na requisição para {url}: {e}")