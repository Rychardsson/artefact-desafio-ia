import re
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
    PolicySection("1", "Atendimento", "Atendimento acolhedor e claro, com informações confirmadas antes de prometer preço, estoque ou prazo."),
    PolicySection("3", "Formas de pagamento", "PIX à vista tem 5% de desconto sobre o preço de tabela. Cartão de crédito em até 12x sem juros. De 1x a 3x, a parcela mínima é R$ 50,00; de 4x a 6x, R$ 80,00; de 7x a 12x, R$ 100,00."),
    PolicySection("4", "Trocas e devoluções", "Arrependimento: 7 dias corridos após o recebimento. Defeito: troca na loja em até 30 dias e garantia legal de 90 dias. A troca por preferência depende da disponibilidade."),
    PolicySection("5", "Frete e entregas", "Na região metropolitana de Campo Grande, o frete custa R$ 35,00 para pedidos até R$ 500,00 e é grátis acima de R$ 500,00. O prazo é de 1 a 3 dias úteis. Para outras cidades, há PAC, SEDEX e Jadlog; o valor depende do CEP, peso e dimensões. Instrumentos grandes podem exigir cotação especial."),
    PolicySection("6", "Promoções e descontos", "Promoções dependem da vigência indicada no catálogo e não são cumulativas. O preço promocional e o preço original devem ser informados com transparência."),
    PolicySection("7", "Privacidade", "A confirmação de dados do pedido exige identificação do cliente. Informações de pedidos não são reveladas a terceiros."),
    PolicySection("8", "Garantia", "A garantia legal para produtos duráveis é de 90 dias, sem prejuízo das regras específicas de troca por defeito."),
]


def _normalize(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(character) != "Mn"
    )


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
        reference_date = today or datetime.now(STORE_ZONE).date()
        delivery_date = date.fromisoformat(order.estimated_delivery) if order.estimated_delivery else None
        overdue = bool(delivery_date and delivery_date < reference_date and order.status not in {"delivered", "cancelled"})
        return OrderView(order.order_id, order.status, order.total, items, order.tracking_code, order.estimated_delivery, overdue)


class ReturnsService:
    def __init__(self, orders: OrderService) -> None:
        self._orders = orders

    def assess(self, session_id: str, order_id: int, reason: str, phone: str | None = None, email: str | None = None, today: date | None = None) -> ReturnAssessment:
        reference_date = today or datetime.now(STORE_ZONE).date()
        order = self._orders.consult(session_id, order_id, phone, email, reference_date)
        if order is None:
            return ReturnAssessment(False, "Não foi possível confirmar os dados do pedido.", None, [])
        if not order.estimated_delivery:
            return ReturnAssessment(False, "O pedido não tem data de recebimento disponível para calcular a janela.", None, ["Podemos encaminhar o caso para a equipe."])
        received = date.fromisoformat(order.estimated_delivery)
        days = (reference_date - received).days
        reason_key = _normalize(reason)
        if "arrepend" in reason_key or "prefer" in reason_key:
            eligible = 0 <= days <= 7
            return ReturnAssessment(eligible, "A janela de 7 dias corridos está aberta." if eligible else "A janela de 7 dias corridos já passou.", (received + timedelta(days=7)).isoformat(), ["Avaliar defeito e garantia legal com a equipe."] if not eligible else [])
        if "defeit" in reason_key:
            eligible = 0 <= days <= 90
            return ReturnAssessment(eligible, "O produto está dentro da garantia legal de 90 dias." if eligible else "A garantia legal de 90 dias já passou.", (received + timedelta(days=90)).isoformat(), [])
        return ReturnAssessment(False, "Preciso entender se o caso é arrependimento, preferência ou defeito.", None, [])


class StoreHoursService:
    def status(self, now: datetime | None = None) -> StoreHours:
        current = (now or datetime.now(STORE_ZONE)).astimezone(STORE_ZONE)
        if current.weekday() < 5:
            opening, closing, label = time(9), time(18), "segunda a sexta, das 9h às 18h"
        elif current.weekday() == 5:
            opening, closing, label = time(9), time(13), "sábado, das 9h às 13h"
        else:
            opening = closing = None
            label = "domingo, fechado"
        if opening and opening <= current.time() < closing:
            return StoreHours(True, label, None)
        next_day = current.date() + timedelta(days=1)
        while next_day.weekday() >= 6:
            next_day += timedelta(days=1)
        return StoreHours(False, label, f"{next_day.isoformat()} às 9h")


def register_handoff(summary: str) -> HumanHandoff:
    if not summary.strip():
        raise ValueError("O resumo do atendimento não pode ficar vazio.")
    protocol = f"EM-{token_hex(4).upper()}"
    return HumanHandoff(protocol, summary.strip(), "A equipe deve retornar em até 24 horas úteis.")
