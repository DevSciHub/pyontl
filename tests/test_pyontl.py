"""Verificações sem rede dos contratos e das falhas de consulta."""

from copy import deepcopy
from datetime import date
import importlib
import unittest
from unittest.mock import Mock, patch

import requests

import pyontl
from pyontl import APIError, IncompleteDownloadError, ResponseError

catalog_module = importlib.import_module("pyontl.catalog")
META = {
    "table": "exemplo", "columns": ["int_idaexemplo", "ano", "uf", "valor"],
    "types": {"int_idaexemplo": "integer", "ano": "integer", "valor": "double precision"},
    "filterableColumns": ["ano", "uf"],
}
TREE = [{"type": "folder", "name": "Infraestrutura", "children": [
    {"type": "folder", "name": "Rodoviário", "children": [
        {"id": 1, "type": "dataset", "name": "Praças de pedágio", "slug": "pedagio",
         "dataset": {"description": "Rodovias federais", "visibility": "public"}},
        {"id": 2, "type": "dataset", "name": "Sem API", "slug": None},
        {"id": 3, "type": "dataset", "name": "Restrito", "slug": "privado",
         "dataset": {"visibility": "private"}},
        {"id": 4, "type": "dataset", "name": "Ferrovias", "slug": None,
         "dataset": {"api_link": "https://ontl-apim.infrasa.gov.br/api/public/datasets/trilhos/"}},
    ]},
]}]


def page(ids, total=3):
    return {"meta": {"total": total}, "data": [{"int_idaexemplo": i} for i in ids]}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        catalog_module._fetch_catalog.cache_clear()
        self.addCleanup(catalog_module._fetch_catalog.cache_clear)

    @patch("pyontl.catalog.make_request", return_value=TREE)
    def test_hierarchy_visibility_missing_slug_and_url(self, request):
        frame = pyontl.catalogo()
        self.assertEqual(len(frame), 3)
        self.assertEqual(frame.iloc[0].caminho,
                         "Infraestrutura > Rodoviário > Praças de pedágio")
        self.assertFalse(frame.iloc[1].consultavel)
        self.assertEqual(frame.iloc[2].dataset, "trilhos")
        request.assert_called_once_with("https://ontl-apim.infrasa.gov.br/api/gerencial/tree")

    @patch("pyontl.catalog.make_request", return_value=TREE)
    def test_search_accents_words_description_and_theme(self, request):
        self.assertEqual(pyontl.buscar("PEDAGIO rodovias", tema="infra").iloc[0].dataset, "pedagio")
        self.assertTrue(pyontl.buscar("pedágio ferrovia").empty)
        self.assertTrue(pyontl.buscar("pedágio", tema="economia").empty)

    @patch("pyontl.catalog.make_request", return_value=TREE)
    def test_cache_refresh_expiration_and_independent_frames(self, request):
        with patch("pyontl.catalog.time.monotonic", return_value=100):
            frame = pyontl.catalogo()
            frame.loc[0, "nome"] = "Alterado"
            self.assertEqual(pyontl.catalogo().iloc[0].nome, "Praças de pedágio")
            self.assertEqual(request.call_count, 1)
            pyontl.catalogo(atualizar=True)
            self.assertEqual(request.call_count, 2)
        with patch("pyontl.catalog.time.monotonic", return_value=4000):
            pyontl.catalogo()
            self.assertEqual(request.call_count, 3)

    def test_empty_and_invalid_catalog(self):
        with patch("pyontl.catalog.make_request", return_value=[]):
            self.assertTrue(pyontl.buscar().empty)
        for invalid in [{"data": []}, [None], [{"children": {}}]]:
            with self.subTest(invalid=invalid):
                with patch("pyontl.catalog.make_request", return_value=invalid):
                    with self.assertRaises(ResponseError):
                        pyontl.catalogo(atualizar=True)

    @patch("pyontl.catalog.make_request", side_effect=APIError("Offline"))
    def test_failure_is_explicit_and_not_cached(self, request):
        for _ in range(2):
            with self.assertRaises(APIError):
                pyontl.catalogo()
        self.assertEqual(request.call_count, 2)


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.metadata_patch = patch("pyontl.client.getMetadados", return_value=deepcopy(META))
        self.metadata = self.metadata_patch.start()
        self.addCleanup(self.metadata_patch.stop)

    @patch("pyontl.client.make_request", side_effect=[page([1, 2]), page([3])])
    def test_all_pages_and_provenance(self, request):
        frame = pyontl.consultar("exemplo", {"ano": 2023, "uf": "SP"}, per_page=2)
        self.assertEqual(frame.int_idaexemplo.tolist(), [1, 2, 3])
        self.assertEqual(frame.attrs["filtros"], {"ano": 2023, "uf": "SP"})
        self.assertEqual(frame.attrs["total"], 3)
        self.assertIn("consultado_em", frame.attrs)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs["params"]["page"], 2)
        self.assertEqual(request.call_args.kwargs["params"]["order_by"], "int_idaexemplo")

    @patch("pyontl.client.make_request", side_effect=[page([1]), APIError("Timeout")])
    def test_failure_on_later_page_never_returns_partial_data(self, request):
        with self.assertRaises(APIError):
            pyontl.consultar("exemplo", {"ano": 2023})

    def test_incomplete_repeated_or_changing_pages(self):
        cases = [
            [page([1]), page([])],
            [page([1]), page([1])],
            [page([1]), page([2], total=4)],
            [page([1, 2], total=1)],
        ]
        for pages in cases:
            with self.subTest(pages=pages):
                with patch("pyontl.client.make_request", side_effect=pages):
                    with self.assertRaises(IncompleteDownloadError):
                        pyontl.consultar("exemplo")

    @patch("pyontl.client.make_request", side_effect=[
        {"data": [{"int_idaexemplo": 1}]}, {"data": [{"int_idaexemplo": 2}]}, {"data": []},
    ])
    def test_pagination_without_total_waits_for_empty_page(self, request):
        self.assertEqual(len(pyontl.consultar("exemplo")), 2)
        self.assertEqual(request.call_count, 3)
        self.assertNotIn("ano", request.call_args.kwargs["params"])

    @patch("pyontl.client.make_request", return_value=page([], total=0))
    def test_empty_result_preserves_columns(self, request):
        frame = pyontl.consultar("exemplo")
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), META["columns"])

    @patch("pyontl.client.make_request")
    def test_filters_and_options_are_validated_before_data_request(self, request):
        cases = [
            {"filtros": {"int_ano": 2023}}, {"filtros": []},
            {"filtros": {"ano": None}}, {"filtros": {"uf": ["SP"]}},
            {"filtros": {"ano": float("nan")}}, {"filtros": {"ano": float("inf")}},
            {"filtros": {"page": 1}}, {"order_by": "missing"},
            {"order_dir": "invalid"}, {"per_page": 0}, {"per_page": True},
            {"per_page": 1001},
        ]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    pyontl.consultar("exemplo", **options)
        request.assert_not_called()

    @patch("pyontl.client.make_request", return_value=page([], total=0))
    def test_dates_are_serialized(self, request):
        pyontl.consultar("exemplo", {"ano": date(2023, 1, 1)})
        self.assertEqual(request.call_args.kwargs["params"]["ano"], "2023-01-01")

    def test_malformed_pages_fail(self):
        for body in [{}, {"data": {}}, {"data": [None]}, {"data": [], "meta": []},
                     {"data": [], "meta": {"total": "3"}}]:
            with self.subTest(body=body):
                with patch("pyontl.client.make_request", return_value=body):
                    with self.assertRaises(ResponseError):
                        pyontl.consultar("exemplo")

    def test_columns_and_metadata_cache(self):
        source = pyontl.dataset("exemplo")
        columns = source.colunas.set_index("nome")
        self.assertTrue(columns.loc["ano", "filtravel"])
        self.assertFalse(columns.loc["valor", "filtravel"])
        self.assertEqual(source.metadados["table"], "exemplo")
        self.metadata.assert_called_once()

    @patch("pyontl.client.catalogo")
    def test_description_comes_from_catalog(self, catalog):
        import pandas as pd
        catalog.return_value = pd.DataFrame([
            {"dataset": "exemplo", "descricao": "Descrição da fonte"},
        ])
        self.assertEqual(pyontl.dataset("exemplo").descricao, "Descrição da fonte")
        self.assertEqual(pyontl.dataset("outro").descricao, "")

    @patch("pyontl.client.make_request", return_value=page([], total=0))
    def test_dataset_without_year_accepts_other_filters(self, request):
        meta = deepcopy(META)
        meta["columns"].remove("ano")
        meta["filterableColumns"] = ["uf"]
        self.metadata.return_value = meta
        pyontl.consultar("exemplo", filtros={"uf": "SP"})
        params = request.call_args.kwargs["params"]
        self.assertEqual(params["uf"], "SP")
        self.assertNotIn("ano", params)

    @patch("pyontl.core.consultar")
    def test_legacy_signature_and_order(self, query):
        pyontl.getDataset(2023, "exemplo", "id", "ano")
        query.assert_called_once_with("exemplo", filtros={"ano": 2023},
                                      order_by="id", order_dir="desc")

    def test_invalid_slug(self):
        for slug in [None, "", "../private", "https://example.com/data", "a?x=1"]:
            with self.subTest(slug=slug):
                with self.assertRaises(ValueError):
                    pyontl.dataset(slug)


class MetadataTests(unittest.TestCase):
    @patch("pyontl.metadata.make_request", return_value=META)
    def test_camel_case_filter_key_without_trailing_space(self, request):
        frame = pyontl.getMetadados_filterableColumns("exemplo")
        self.assertEqual(frame.column_name.tolist(), ["ano", "uf"])
        self.assertEqual(frame.dataset.tolist(), ["exemplo", "exemplo"])

    @patch("pyontl.metadata.make_request", return_value={
        **META, "filterable_columns": [],
    })
    def test_empty_snake_case_filter_list_is_respected(self, request):
        self.assertTrue(pyontl.getMetadados_filterableColumns("exemplo").empty)

    def test_malformed_metadata(self):
        for meta in [{}, {"columns": [None]}, {**META, "types": []},
                     {**META, "filterableColumns": "ano"}]:
            with self.subTest(meta=meta):
                with patch("pyontl.metadata.make_request", return_value=meta):
                    with self.assertRaises(ResponseError):
                        pyontl.getMetadados("exemplo")


class TransportTests(unittest.TestCase):
    def test_transient_status_is_retried(self):
        from io import BytesIO
        from urllib3 import HTTPConnectionPool
        from urllib3.response import HTTPResponse
        from pyontl.utils import _session

        # Exercita o mecanismo real de retry do urllib3 sem acessar a rede.
        policy = _session.get_adapter("https://").max_retries
        pool = HTTPConnectionPool("example.com")
        with patch.object(pool, "_make_request", side_effect=[
            HTTPResponse(body=BytesIO(b"busy"), status=503, preload_content=False),
            HTTPResponse(body=BytesIO(b'{"ok": true}'), status=200, preload_content=False),
        ]) as send:
            response = pool.urlopen("GET", "/", retries=policy)
        self.assertEqual(response.status, 200)
        self.assertEqual(send.call_count, 2)

    @patch("pyontl.utils._session.get")
    def test_http_error_exposes_api_message_and_status(self, get):
        get.return_value = Mock(ok=False, status_code=400)
        get.return_value.json.return_value = {"message": "Informe um filtro"}
        from pyontl.utils import make_request
        with self.assertRaisesRegex(APIError, "Informe um filtro") as caught:
            make_request("https://example.com")
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.url, "https://example.com")

    @patch("pyontl.utils._session.get")
    def test_non_json_success_and_html_error(self, get):
        from pyontl.utils import make_request
        for ok, exception in [(True, ResponseError), (False, APIError)]:
            get.return_value = Mock(ok=ok, status_code=500)
            get.return_value.json.side_effect = ValueError("HTML")
            with self.assertRaises(exception):
                make_request("https://example.com")

    @patch("pyontl.utils._session.get", side_effect=requests.exceptions.Timeout("timeout"))
    def test_timeout(self, get):
        from pyontl.utils import make_request
        with self.assertRaises(APIError):
            make_request("https://example.com")


if __name__ == "__main__":
    unittest.main()
