from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from .models import CartLine, InstallmentOption, PurchaseConditions, ShippingOption

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_conditions(lines: Iterable[CartLine], city: str) -> PurchaseConditions:
    cart = list(lines)
    if not cart:
        raise ValueError("At least one item is required.")
    if any(line.quantity < 1 for line in cart):
        raise ValueError("A quantidade de cada item deve ser positiva.")

    subtotal = _money(sum((line.item.final_price * line.quantity for line in cart), Decimal("0")))
    pix_eligible = all(line.item.promotion is None for line in cart)
    pix_total = _money(subtotal * Decimal("0.95")) if pix_eligible else None

    installments: list[InstallmentOption] = []
    for count in range(1, 13):
        amount = _money(subtotal / count)
        if count <= 3 and (count == 1 or subtotal >= Decimal("50")):
            installments.append(InstallmentOption(count, amount))
        elif 4 <= count <= 6 and amount >= Decimal("80"):
            installments.append(InstallmentOption(count, amount))
        elif 7 <= count <= 12 and amount >= Decimal("100"):
            installments.append(InstallmentOption(count, amount))

    special = any(
        keyword in f"{line.item.product.name} {line.item.product.description or ''}".casefold()
        for line in cart
        for keyword in ("bateria", "piano", "contrabaixo")
    )
    normalized_city = city.casefold().strip()
    notes: list[str] = []
    if special:
        notes.append("Large instruments may require a special shipping quote.")

    if normalized_city == "campo grande":
        shipping_price = Decimal("0") if subtotal > Decimal("500") else Decimal("35")
        shipping_options = [
            ShippingOption("Store courier", "1 to 3 business days", shipping_price)
        ]
    else:
        shipping_price = None
        shipping_options = [
            ShippingOption("PAC (Correios)", "5 to 12 business days", None),
            ShippingOption("SEDEX (Correios)", "2 to 5 business days", None),
            ShippingOption("Jadlog", "3 to 8 business days", None),
        ]
        notes.append("Shipping outside the metropolitan region is calculated from ZIP code, weight, and dimensions.")

    return PurchaseConditions(
        subtotal=subtotal,
        pix_total=pix_total,
        installments=installments,
        shipping_price=shipping_price,
        shipping_options=shipping_options,
        special_freight_quote=special,
        notes=notes,
    )
