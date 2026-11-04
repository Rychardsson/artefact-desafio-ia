from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from emporio_agent import CartLine, Catalog, CatalogSearch, calculate_conditions, load_data


DATA = Path(__file__).parents[1] / "Desafio Técnico AI Engineer 2026" / "data"


def test_loads_data_and_keeps_audit():
    data = load_data(DATA)
    assert len(data.products) == 65
    assert len(data.orders) == 20
    assert isinstance(data.audits, list)


def test_hides_unavailable_products():
    result = Catalog(load_data(DATA)).search(CatalogSearch(query="violões", max_price=Decimal("1000")))
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


def test_calculates_pix_and_installments_without_float_rounding():
    catalog = Catalog(load_data(DATA))
    takamine = catalog.search(CatalogSearch(query="Takamine GD20")).items[0]
    conditions = calculate_conditions([CartLine(takamine)], "Campo Grande")
    assert conditions.subtotal == Decimal("2199.00")
    assert conditions.pix_total == Decimal("2089.05")
    assert conditions.installments[-1].count == 12
    assert conditions.installments[-1].amount == Decimal("183.25")


def test_pix_is_not_available_for_promoted_items():
    catalog = Catalog(load_data(DATA))
    ohana = catalog.search(CatalogSearch(query="Ohana CK-20")).items[0]
    conditions = calculate_conditions([CartLine(ohana)], "Campo Grande")
    assert conditions.pix_total is None


def test_installment_minimum_and_strict_free_shipping_threshold():
    catalog = Catalog(load_data(DATA))
    item = catalog.search(CatalogSearch(query="Ohana CK-20")).items[0]
    conditions = calculate_conditions([CartLine(item)], "Campo Grande")
    assert [option.count for option in conditions.installments] == [1, 2, 3, 4, 5]
    assert conditions.shipping_price == Decimal("35")


def test_exactly_five_hundred_is_not_free_shipping():
    catalog = Catalog(load_data(DATA))
    item = catalog.search(CatalogSearch(query="Ohana CK-20")).items[0]
    exact_threshold = replace(item, final_price=Decimal("500"))
    conditions = calculate_conditions([CartLine(exact_threshold)], "Campo Grande")
    assert conditions.shipping_price == Decimal("35")


def test_one_hundred_fifty_nine_ninety_allows_only_three_installments():
    catalog = Catalog(load_data(DATA))
    item = catalog.search(CatalogSearch(query="Ohana CK-20")).items[0]
    item = replace(item, final_price=Decimal("159.90"))
    conditions = calculate_conditions([CartLine(item)], "Campo Grande")
    assert [option.count for option in conditions.installments] == [1, 2, 3]
