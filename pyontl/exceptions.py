"""Erros públicos da biblioteca."""


class ONTLError(Exception):
    """Erro ao acessar ou interpretar os dados do ONTL."""


class APIError(ONTLError):
    """Falha HTTP ou de conexão; inclui URL e status quando disponíveis."""

    def __init__(self, message, url=None, status_code=None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class ResponseError(APIError):
    """Resposta incompatível com o contrato esperado."""


class IncompleteDownloadError(ONTLError):
    """A paginação não recuperou todos os registros declarados."""
