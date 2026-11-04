import csv
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Category, Customer, DataAudit, Order, OrderItem, Product, Promotion

FILES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
}


@dataclass(frozen=True)
class DataStore:
    categories: list[Category]
    customers: list[Customer]
    order_items: list[OrderItem]
    orders: list[Order]
    products: list[Product]
    promotions: list[Promotion]
    audits: list[DataAudit]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _int(value: str, field: str, source: str, row: int, audits: list[DataAudit]) -> int:
    try:
        return int(value)
    except ValueError:
        audits.append(DataAudit(source, row, field, f"Invalid integer value: {value}"))
        return 0


def _decimal(value: str, field: str, source: str, row: int, audits: list[DataAudit]) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation:
        audits.append(DataAudit(source, row, field, f"Invalid decimal value: {value}"))
        return Decimal("0")


def _optional(value: str) -> str | None:
    return value.strip() or None


def load_data(data_directory: str | Path) -> DataStore:
    directory = Path(data_directory)
    audits: list[DataAudit] = []
    category_rows = _read(directory / FILES["categories"])
    customer_rows = _read(directory / FILES["customers"])
    order_item_rows = _read(directory / FILES["order_items"])
    order_rows = _read(directory / FILES["orders"])
    product_rows = _read(directory / FILES["products"])
    promotion_rows = _read(directory / FILES["promotions"])

    products: list[Product] = []
    for row_number, item in enumerate(product_rows, 2):
        try:
            specs = json.loads(item["specs"] or "{}")
        except json.JSONDecodeError:
            specs = {}
            audits.append(DataAudit(FILES["products"], row_number, "specs", "Invalid JSON"))
        status = item["status"]
        if status not in {"active", "coming_soon", "discontinued"}:
            audits.append(DataAudit(FILES["products"], row_number, "status", f"Status desconhecido: {status}"))
        products.append(
            Product(
                product_id=_int(item["product_id"], "product_id", FILES["products"], row_number, audits),
                price=_decimal(item["price_brl"], "price_brl", FILES["products"], row_number, audits),
                name=item["name"],
                category_id=_int(item["category_id"], "category_id", FILES["products"], row_number, audits),
                description=_optional(item["description"]),
                stock_quantity=_int(item["stock_quantity"], "stock_quantity", FILES["products"], row_number, audits),
                status=status,
                specs=specs,
                created_at=item["created_at"],
            )
        )

    return DataStore(
        categories=[
            Category(_int(x["category_id"], "category_id", FILES["categories"], i, audits), x["name"], _optional(x["description"]))
            for i, x in enumerate(category_rows, 2)
        ],
        customers=[
            Customer(_int(x["customer_id"], "customer_id", FILES["customers"], i, audits), x["name"], "".join(c for c in x["phone"] if c.isdigit()), x["email"].strip().lower(), x["city"])
            for i, x in enumerate(customer_rows, 2)
        ],
        order_items=[
            OrderItem(_int(x["order_id"], "order_id", FILES["order_items"], i, audits), _int(x["quantity"], "quantity", FILES["order_items"], i, audits), _int(x["product_id"], "product_id", FILES["order_items"], i, audits))
            for i, x in enumerate(order_item_rows, 2)
        ],
        orders=[
            Order(_int(x["order_id"], "order_id", FILES["orders"], i, audits), _int(x["customer_id"], "customer_id", FILES["orders"], i, audits), x["order_date"], x["status"], _decimal(x["total_brl"], "total_brl", FILES["orders"], i, audits), x["payment_method"], _optional(x["tracking_code"]), _optional(x["estimated_delivery"]), _optional(x["notes"]))
            for i, x in enumerate(order_rows, 2)
        ],
        products=products,
        promotions=[
            Promotion(_int(x["promotion_id"], "promotion_id", FILES["promotions"], i, audits), _int(x["product_id"], "product_id", FILES["promotions"], i, audits), _decimal(x["discount_percent"], "discount_percent", FILES["promotions"], i, audits), _optional(x["description"]), x["is_active"] == "1")
            for i, x in enumerate(promotion_rows, 2)
        ],
        audits=audits,
    )
