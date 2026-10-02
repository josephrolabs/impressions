"""Product catalog: SKU -> unit price lookup."""

_PRICES = {
    "book": 12.99,
    "pen": 1.50,
    "lamp": 24.00,
    "mug": 8.25,
}


class Catalog:
    """Look up unit prices for known SKUs."""

    def get_price(self, sku):
        """Return the unit price for ``sku``.

        Raises:
            KeyError: If ``sku`` is not in the catalog.
        """
        return _PRICES[sku]

    def has_sku(self, sku):
        """Return True when ``sku`` is a known product."""
        return sku in _PRICES
