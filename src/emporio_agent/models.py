from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

ProductStatus = Literal["active", "coming_soon", "discontinued"]


@dataclass(frozen=True)
class Product:
    product_id: int
    price: Decimal
    name: str
    category_id: int
    description: str | None
    stock_quantity: int
    status: ProductStatus
    specs: dict[str, str]
    created_at: str


@dataclass(frozen=True)
class Category:
    category_id: int
    name: str
    description: str | None


@dataclass(frozen=True)
class Promotion:
    promotion_id: int
    product_id: int
    discount_percent: Decimal
    description: str | None
    is_active: bool


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    phone: str
    email: str
    city: str


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    order_date: str
    status: str
    total: Decimal
    payment_method: str
    tracking_code: str | None
    estimated_delivery: str | None
    notes: str | None


@dataclass(frozen=True)
class OrderItem:
    order_id: int
    quantity: int
    product_id: int


@dataclass(frozen=True)
class DataAudit:
    source: str
    row: int
    field: str
    message: str


@dataclass(frozen=True)
class CatalogItem:
    product: Product
    category: Category | None
    original_price: Decimal
    final_price: Decimal
    promotion: Promotion | None
    available: bool


@dataclass(frozen=True)
class CatalogSearch:
    query: str | None = None
    category_id: int | None = None
    max_price: Decimal | None = None
    min_price: Decimal | None = None
    promotions_only: bool = False
    include_unavailable: bool = False
    sort: Literal["price_asc", "price_desc", "relevance"] = "price_asc"


@dataclass(frozen=True)
class CatalogResult:
    items: list[CatalogItem]
    hidden_unavailable: int
    alternatives: list[CatalogItem]
