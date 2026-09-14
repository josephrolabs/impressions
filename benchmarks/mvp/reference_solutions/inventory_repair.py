from fixtures.inventory import apply_delta


def solve(records):
    stock={}
    for sku,delta in records:
        if not isinstance(sku,str) or not sku: raise ValueError("sku")
        apply_delta(stock, sku, delta)
    if any(value<0 for value in stock.values()): raise ValueError("stock")
    return dict(sorted(stock.items()))
