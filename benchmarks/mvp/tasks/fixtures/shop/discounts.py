"""Discount policy for coupon codes."""


class DiscountPolicy:
    """Apply a coupon to an order subtotal exactly once."""

    def apply(self, subtotal, coupon):
        """Return the total after applying ``coupon`` to ``subtotal``.

        ``coupon`` may be None (no discount). Supported coupons:

        - ``"SAVE10"``: 10% off the subtotal.
        - ``"FLAT5"``: $5 off, requires a $20 minimum subtotal.

        Raises:
            ValueError: If the coupon is unknown or its minimum is not met.
        """
        if coupon is None:
            return subtotal
        if coupon == "SAVE10":
            return subtotal * 0.9
        if coupon == "FLAT5":
            if subtotal < 20:
                raise ValueError("FLAT5 requires a $20 minimum subtotal")
            return subtotal - 5
        raise ValueError(f"unknown coupon: {coupon}")
