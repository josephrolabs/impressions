"""Checkout pipeline.

WARNING: this module contains known bugs. Read it carefully, but do not
trust it: a correct solution must not rely on ``Checkout.total``.
"""

from fixtures.shop.catalog import Catalog
from fixtures.shop.discounts import DiscountPolicy


class Checkout:
    """Total an order of (sku, quantity) line items."""

    def __init__(self):
        self.catalog = Catalog()
        self.policy = DiscountPolicy()

    def total(self, items, coupon=None):
        # BUG 1: the coupon is applied to every line item instead of once
        # to the order subtotal, so FLAT5 subtracts $5 per line.
        # BUG 2: unknown SKUs surface as a bare KeyError from the catalog
        # instead of a ValueError.
        total = 0.0
        for sku, qty in items:
            line = self.catalog.get_price(sku) * qty
            total += self.policy.apply(line, coupon)
        return round(total, 2)
