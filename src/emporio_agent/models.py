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


@dataclass(frozen=True)
class CartLine:
    item: CatalogItem
    quantity: int = 1


@dataclass(frozen=True)
class InstallmentOption:
    count: int
    amount: Decimal


@dataclass(frozen=True)
class ShippingOption:
    method: str
    estimated_days: str
    price: Decimal | None
    tracking_and_insurance: bool = True


@dataclass(frozen=True)
class PurchaseConditions:
    subtotal: Decimal
    pix_total: Decimal | None
    installments: list[InstallmentOption]
    shipping_price: Decimal | None
    shipping_options: list[ShippingOption]
    special_freight_quote: bool
    notes: list[str]


@dataclass(frozen=True)
class OrderItemView:
    product_id: int
    name: str
    quantity: int


@dataclass(frozen=True)
class OrderView:
    order_id: int
    status: str
    total: Decimal
    items: list[OrderItemView]
    tracking_code: str | None
    estimated_delivery: str | None
    delivery_overdue: bool


@dataclass(frozen=True)
class ReturnAssessment:
    eligible: bool
    reason: str
    deadline: str | None
    alternatives: list[str]


@dataclass(frozen=True)
class StoreHours:
    is_open: bool
    current_period: str
    next_opening: str | None


@dataclass(frozen=True)
class PolicySection:
    number: str
    title: str
    content: str


@dataclass(frozen=True)
class HumanHandoff:
    protocol: str
    message: str
    expected_response: str
