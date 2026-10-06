"""Canonical solution: diagnose the checkout bugs, compose the working modules."""

from fixtures.shop.catalog import Catalog
from fixtures.shop.discounts import DiscountPolicy


def checkout_total(items, coupon=None):
    catalog = Catalog()
    policy = DiscountPolicy()

    subtotal = 0.0
    for sku, qty in items:
        if not catalog.has_sku(sku):
            raise ValueError(f"unknown SKU: {sku}")
        subtotal += catalog.get_price(sku) * qty

    # The coupon applies once to the order subtotal, not per line item.
    total = policy.apply(subtotal, coupon)
    return round(total, 2)
