from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from emporio_agent import (
    OrderService,
    PolicyService,
    ReturnsService,
    StoreHoursService,
    StoreInformationService,
    load_data,
    register_handoff,
)


DATA = Path(__file__).parents[1] / "Desafio Técnico AI Engineer 2026" / "data"
ZONE = ZoneInfo("America/Campo_Grande")


def test_policy_search_finds_defect_section():
    sections = PolicyService().search("troca por defeito")
    assert sections
    assert sections[0].number == "4"


def test_order_requires_phone_and_blocks_after_three_failures():
    data = load_data(DATA)
    service = OrderService(data)
    assert service.consult("session", 8, phone="00000000000") is None
    assert service.consult("session", 8, phone="00000000000") is None
    assert service.consult("session", 8, phone="00000000000") is None
    assert service.consult("session", 8, phone="67996547821") is None
    order = service.consult("new-session", 8, phone="67996547821", today=date(2026, 11, 4))
    assert order is not None
    assert order.delivery_overdue is True
    assert order.total == Decimal("349.9")


def test_return_window_uses_delivery_date_proxy():
    data = load_data(DATA)
    order_service = OrderService(data)
    returns = ReturnsService(order_service)
    assessment = returns.assess(
        "return-session",
        8,
        "arrependimento",
        phone="67996547821",
        today=date(2026, 3, 10),
    )
    assert assessment.eligible is False
    assert assessment.deadline == "2026-03-07"


def test_hours():
    service = StoreHoursService()
    open_status = service.status(datetime(2026, 11, 4, 10, 0, tzinfo=ZONE))
    closed_status = service.status(datetime(2026, 11, 7, 14, 0, tzinfo=ZONE))
    assert open_status.is_open is True
    assert closed_status.is_open is False


def test_handoff_has_protocol_and_sla():
    handoff = register_handoff("Pedido 8 está atrasado.")
    assert handoff.protocol.startswith("EM-")
    assert "24 horas úteis" in handoff.expected_response


def test_store_information_is_explicit():
    information = StoreInformationService().get(datetime(2026, 11, 4, 10, 0, tzinfo=ZONE))
    assert information["address"] == "Rua 14 de Maio, 3200 - Centro, Campo Grande - MS, CEP 79202-333"
    assert information["hours"].is_open is True


def test_empório_now_reproduces_approved_return_window(monkeypatch):
    monkeypatch.setenv("EMPORIO_NOW", "2026-03-01T10:00:00-04:00")
    data = load_data(DATA)
    assessment = ReturnsService(OrderService(data)).assess(
        "frozen-session",
        8,
        "arrependimento",
        phone="67996547821",
    )
    assert assessment.eligible is True
    assert assessment.deadline == "2026-03-07"


def test_invalid_empório_now_is_explicit(monkeypatch):
    monkeypatch.setenv("EMPORIO_NOW", "not-a-date")
    with pytest.raises(ValueError, match="EMPORIO_NOW"):
        StoreHoursService().status()
