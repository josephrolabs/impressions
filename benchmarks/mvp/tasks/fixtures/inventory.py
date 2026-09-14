def apply_delta(stock, sku, delta):
    """Legacy helper: deliberately does not validate negative final stock."""
    stock[sku] = stock.get(sku, 0) + delta
