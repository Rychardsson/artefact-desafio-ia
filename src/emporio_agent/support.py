import re
import os
import unicodedata
from datetime import date, datetime, time, timedelta
from secrets import token_hex
from zoneinfo import ZoneInfo

from .data_store import DataStore
from .models import (
    HumanHandoff,
    OrderItemView,
    OrderView,
    PolicySection,
    ReturnAssessment,
    StoreHours,
)

STORE_ZONE = ZoneInfo("America/Campo_Grande")

POLICIES = [
    PolicySection("1", "Customer service", "Friendly and clear service, with confirmed information before promising prices, stock, or delivery times."),
    PolicySection("3", "Payment methods", "PIX paid upfront receives a 5% discount from the list price. Credit cards support up to 12 interest-free installments. From 1 to 3 installments, the minimum installment is R$ 50.00; from 4 to 6, R$ 80.00; from 7 to 12, R$ 100.00."),
    PolicySection("4", "Returns and exchanges", "Change of mind: 7 calendar days after receipt. Defect: in-store exchange within 30 days and a 90-day legal warranty. Preference exchanges depend on availability."),
    PolicySection("5", "Shipping and delivery", "In metropolitan Campo Grande, shipping costs R$ 35.00 for orders up to R$ 500.00 and is free above R$ 500.00. Delivery takes 1 to 3 business days. Other cities can use PAC, SEDEX, or Jadlog; price depends on ZIP code, weight, and dimensions. Large instruments may require a special quote."),
    PolicySection("6", "Promotions and discounts", "Promotions depend on the catalog status and do not stack. The original and promotional prices must be disclosed clearly."),
    PolicySection("7", "Privacy", "Order-data confirmation requires customer identification. Order information is not disclosed to third parties."),
    PolicySection("8", "Warranty", "Durable products have a 90-day legal warranty, without affecting the specific defect-exchange rules."),
]


def _normalize(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(character) != "Mn"
    )


def _now() -> datetime:
    configured = os.getenv("EMPORIO_NOW")
    if not configured:
        return datetime.now(STORE_ZONE)
    try:
        parsed = datetime.fromisoformat(configured)
    except ValueError as error:
        raise ValueError("EMPORIO_NOW must use ISO-8601 format.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=STORE_ZONE)
    return parsed.astimezone(STORE_ZONE)


class PolicyService:
    def search(self, query: str, limit: int = 3) -> list[PolicySection]:
        if not query.strip():
            return POLICIES[:limit]
        terms = set(re.findall(r"\w+", _normalize(query)))
        ranked = sorted(
            POLICIES,
            key=lambda section: sum(
                term in _normalize(f"{section.title} {section.content}")
                for term in terms
            ),
            reverse=True,
        )
        return [section for section in ranked[:limit] if any(
            term in _normalize(f"{section.title} {section.content}") for term in terms
        )]


class OrderService:
    def __init__(self, data: DataStore) -> None:
        self._data = data
        self._failures: dict[str, int] = {}

    def consult(self, session_id: str, order_id: int, phone: str | None = None, email: str | None = None, today: date | None = None) -> OrderView | None:
        if self._failures.get(session_id, 0) >= 3:
            return None
        order = next((candidate for candidate in self._data.orders if candidate.order_id == order_id), None)
        customer = next((candidate for candidate in self._data.customers if candidate.customer_id == order.customer_id), None) if order else None
        normalized_phone = "".join(character for character in (phone or "") if character.isdigit())
        email_matches = [candidate for candidate in self._data.customers if candidate.email == (email or "").strip().casefold()]
        valid = bool(customer and (
            normalized_phone and customer.phone == normalized_phone
            or email and len(email_matches) == 1 and email_matches[0].customer_id == customer.customer_id
        ))
        if not valid:
            self._failures[session_id] = self._failures.get(session_id, 0) + 1
            return None
        items = [
            OrderItemView(item.product_id, next((product.name for product in self._data.products if product.product_id == item.product_id), "Produto"), item.quantity)
            for item in self._data.order_items if item.order_id == order.order_id
        ]
        reference_date = today or _now().date()
        delivery_date = date.fromisoformat(order.estimated_delivery) if order.estimated_delivery else None
        overdue = bool(delivery_date and delivery_date < reference_date and order.status not in {"delivered", "cancelled"})
        return OrderView(order.order_id, order.status, order.total, items, order.tracking_code, order.estimated_delivery, overdue)


class ReturnsService:
    def __init__(self, orders: OrderService) -> None:
        self._orders = orders

    def assess(self, session_id: str, order_id: int, reason: str, phone: str | None = None, email: str | None = None, today: date | None = None) -> ReturnAssessment:
        reference_date = today or _now().date()
        order = self._orders.consult(session_id, order_id, phone, email, reference_date)
        if order is None:
            return ReturnAssessment(False, "The order details could not be validated.", None, [])
        if not order.estimated_delivery:
            return ReturnAssessment(False, "The order has no receipt date available to calculate the window.", None, ["We can refer this case to the support team."])
        received = date.fromisoformat(order.estimated_delivery)
        days = (reference_date - received).days
        reason_key = _normalize(reason)
        if "arrepend" in reason_key or "prefer" in reason_key:
            eligible = 0 <= days <= 7
            return ReturnAssessment(eligible, "The seven-day window is open." if eligible else "The seven-day window has expired.", (received + timedelta(days=7)).isoformat(), ["Assess the defect and legal warranty with the support team."] if not eligible else [])
        if "defeit" in reason_key:
            eligible = 0 <= days <= 90
            return ReturnAssessment(eligible, "The product is within the 90-day legal warranty." if eligible else "The 90-day legal warranty has expired.", (received + timedelta(days=90)).isoformat(), [])
        return ReturnAssessment(False, "I need to know whether this is a change of mind, preference, or defect.", None, [])


class StoreHoursService:
    def status(self, now: datetime | None = None) -> StoreHours:
        current = (now or _now()).astimezone(STORE_ZONE)
        if current.weekday() < 5:
            opening, closing, label = time(9), time(18), "Monday to Friday, 9 AM to 6 PM"
        elif current.weekday() == 5:
            opening, closing, label = time(9), time(13), "Saturday, 9 AM to 1 PM"
        else:
            opening = closing = None
            label = "Sunday, closed"
        if opening and opening <= current.time() < closing:
            return StoreHours(True, label, None)
        next_day = current.date() + timedelta(days=1)
        while next_day.weekday() >= 6:
            next_day += timedelta(days=1)
        return StoreHours(False, label, f"{next_day.isoformat()} at 9 AM")


class StoreInformationService:
    def __init__(self) -> None:
        self._hours = StoreHoursService()

    def get(self, now: datetime | None = None) -> dict[str, object]:
        return {
            "address": "Rua 14 de Maio, 3200 - Centro, Campo Grande - MS, CEP 79202-333",
            "phone": "(67) 3341-4444",
            "email": "contato@emporiodamusica.com.br",
            "hours": self._hours.status(now),
        }


def register_handoff(summary: str) -> HumanHandoff:
    if not summary.strip():
        raise ValueError("The handoff summary cannot be empty.")
    protocol = f"EM-{token_hex(4).upper()}"
    return HumanHandoff(protocol, summary.strip(), "The support team should respond within 24 business hours.")
