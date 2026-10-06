import pytest

from solution import checkout_total


def test_no_coupon_totals_line_items():
    assert checkout_total([("book", 2), ("pen", 4)]) == round(2 * 12.99 + 4 * 1.50, 2)


def test_save10_takes_ten_percent_off_order_total():
    # A percentage discount is distributive, so per-line and subtotal
    # application of SAVE10 coincide; this test pins SAVE10's arithmetic.
    # The per-line bug is discriminated by the FLAT5 tests below, where a
    # flat amount (and its minimum) makes the two readings differ.
    assert checkout_total([("book", 1), ("pen", 1)], "SAVE10") == round((12.99 + 1.50) * 0.9, 2)


def test_flat5_applies_once_not_per_line():
    # Buggy checkout subtracts $5 from every line: (24.00 - 5) + (25.98 - 5) = 39.98.
    # Both lines clear the $20 minimum, so the per-line reading fails on
    # the amount alone, not on an exception.
    assert checkout_total([("lamp", 1), ("book", 2)], "FLAT5") == round(24.00 + 2 * 12.99 - 5, 2)


def test_flat5_minimum_subtotal_enforced():
    with pytest.raises(ValueError):
        checkout_total([("pen", 1)], "FLAT5")


def test_unknown_sku_raises_value_error_not_key_error():
    with pytest.raises(ValueError):
        checkout_total([("nope", 1)])


def test_unknown_coupon_raises_value_error():
    with pytest.raises(ValueError):
        checkout_total([("book", 2)], "BOGUS")


def test_empty_cart_totals_zero():
    assert checkout_total([]) == 0.0


def test_empty_cart_with_coupon_still_validates():
    with pytest.raises(ValueError):
        checkout_total([], "FLAT5")
