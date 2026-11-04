from decimal import Decimal
from pathlib import Path

from emporio_agent import Catalog, CatalogSearch, load_data


DATA = Path(__file__).parents[1] / "Desafio Técnico AI Engineer 2026" / "data"


def test_loads_data_and_keeps_audit():
    data = load_data(DATA)
    assert len(data.products) == 65
    assert len(data.orders) == 20
    assert isinstance(data.audits, list)


def test_hides_unavailable_products():
    result = Catalog(load_data(DATA)).search(CatalogSearch(query="violão", max_price=Decimal("1000")))
    assert all(item.available for item in result.items)
    assert all(item.product.status == "active" for item in result.items)


def test_uses_only_active_promotions():
    catalog = Catalog(load_data(DATA))
    takamine = catalog.search(CatalogSearch(query="Takamine GD20", include_unavailable=True)).items[0]
    assert takamine.final_price == Decimal("2199")
    ohana = catalog.search(CatalogSearch(query="Ohana CK-20")).items[0]
    assert ohana.final_price == Decimal("439.20")
    assert ohana.promotion is not None
    assert ohana.promotion.discount_percent == Decimal("20")
