from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from .models import CartLine, InstallmentOption, PurchaseConditions, ShippingOption

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_conditions(lines: Iterable[CartLine], city: str) -> PurchaseConditions:
    cart = list(lines)
    if not cart:
        raise ValueError("É necessário informar ao menos um item.")
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
        notes.append("Instrumentos de grande porte podem exigir frete especial com cotação individual.")

    if normalized_city == "campo grande":
        shipping_price = Decimal("0") if subtotal > Decimal("500") else Decimal("35")
        shipping_options = [
            ShippingOption("Motoboy próprio", "1 a 3 dias úteis", shipping_price)
        ]
    else:
        shipping_price = None
        shipping_options = [
            ShippingOption("PAC (Correios)", "5 a 12 dias úteis", None),
            ShippingOption("SEDEX (Correios)", "2 a 5 dias úteis", None),
            ShippingOption("Jadlog", "3 a 8 dias úteis", None),
        ]
        notes.append("O valor do frete fora da região metropolitana é calculado pelo CEP, peso e dimensões.")

    return PurchaseConditions(
        subtotal=subtotal,
        pix_total=pix_total,
        installments=installments,
        shipping_price=shipping_price,
        shipping_options=shipping_options,
        special_freight_quote=special,
        notes=notes,
    )
