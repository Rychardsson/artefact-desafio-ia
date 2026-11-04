from decimal import Decimal, ROUND_HALF_UP

from .data_store import DataStore
from .models import CatalogItem, CatalogResult, CatalogSearch


class Catalog:
    def __init__(self, data: DataStore) -> None:
        self._data = data

    def _item(self, product_id: int) -> CatalogItem | None:
        product = next((p for p in self._data.products if p.product_id == product_id), None)
        if product is None:
            return None
        promotion = max(
            (p for p in self._data.promotions if p.product_id == product_id and p.is_active),
            key=lambda p: p.discount_percent,
            default=None,
        )
        final_price = product.price
        if promotion:
            final_price = (product.price * (Decimal("100") - promotion.discount_percent) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        category = next((c for c in self._data.categories if c.category_id == product.category_id), None)
        return CatalogItem(product, category, product.price, final_price, promotion, product.status == "active" and product.stock_quantity > 0)

    def search(self, criteria: CatalogSearch = CatalogSearch()) -> CatalogResult:
        items = [item for product in self._data.products if (item := self._item(product.product_id)) is not None]
        query = criteria.query.casefold().strip() if criteria.query else None
        if query:
            items = [item for item in items if query in f"{item.product.name} {item.category.name if item.category else ''}".casefold()]
        if criteria.category_id is not None:
            items = [item for item in items if item.product.category_id == criteria.category_id]
        if criteria.max_price is not None:
            items = [item for item in items if item.final_price <= criteria.max_price]
        if criteria.min_price is not None:
            items = [item for item in items if item.final_price >= criteria.min_price]
        if criteria.promotions_only:
            items = [item for item in items if item.promotion is not None]
        hidden = sum(not item.available for item in items)
        visible = items if criteria.include_unavailable else [item for item in items if item.available]
        visible.sort(key=lambda item: item.final_price, reverse=criteria.sort == "price_desc")
        alternatives = []
        if query and not visible:
            alternatives = [item for item in items if item.available][:3]
        return CatalogResult(visible, hidden, alternatives)
